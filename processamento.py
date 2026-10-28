"""Leitura validada dos CSVs e montagem de uma linha por estabelecimento."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import math
import os
import pandas as pd
from referencias import classe_cnae

ARQUIVOS = (
    'empresas', 'enderecos_estabelecimentos', 'sinais_financeiros_operacionais',
    'bens_cadastrados', 'territorio', 'catalogo_coberturas_fixas_planos',
    'dicionario_dados', 'template_resultado_times', 'template_coberturas_times',
)
CHAVES = ['empresa_id', 'imovel_id']
TIPOS_ELETRICOS = {
    'EQUIPAMENTO_REFRIGERACAO', 'EQUIPAMENTO_ELETRONICO',
    'EQUIPAMENTO_INFORMATICA', 'EQUIPAMENTO_OFICINA', 'EQUIPAMENTO_MEDICO',
    'MAQUINA', 'EQUIPAMENTO_BELEZA', 'EQUIPAMENTO_COZINHA',
}
NULOS = {'', 'NAO_DISPONIVEL', 'NÃO_DISPONIVEL', 'NA', 'N/A', 'NULL', 'NAN'}


def localizar_referencias(pasta=None):
    if pasta or os.environ.get('BB_DATATHON_REFERENCIAS'):
        return Path(pasta or os.environ['BB_DATATHON_REFERENCIAS'])
    raiz=Path(__file__).parent
    local=raiz/'data'/'referencias'
    return local if local.exists() else raiz/'references'


def caminho_referencia(nome, pasta=None):
    """Um SSP local isolado não oculta os snapshots distribuídos de clima/NR-4."""
    selecionada = localizar_referencias(pasta)
    caminho = selecionada/nome
    raiz = Path(__file__).parent
    if not caminho.exists() and selecionada.resolve() == (raiz/'data'/'referencias').resolve():
        distribuida = raiz/'references'/nome
        if distribuida.exists():
            return distribuida
    return caminho


def numero(valor):
    """Aceita zero; rejeita ausências, valores negativos e não finitos."""
    try:
        n = float(valor)
        return n if math.isfinite(n) and n >= 0 else None
    except (TypeError, ValueError):
        return None


def localizar_dados(pasta=None):
    if pasta:
        caminho = Path(pasta).expanduser().resolve()
        if not (caminho / 'empresas.csv').is_file():
            raise ValueError(f'Pasta sem empresas.csv: {caminho}')
        return caminho
    raiz = Path(__file__).resolve().parent
    for caminho in (raiz / 'data' / 'desenvolvimento',
                    raiz.parent / 'Seguro_Empresarial_Desenvolvimento'):
        if (caminho / 'empresas.csv').is_file():
            return caminho
    raise ValueError('Informe a pasta dos nove CSVs ou execute scripts/importar_dados.py.')


def ler_csv(caminho):
    # O dicionário é lido antes dos demais arquivos.
    return pd.read_csv(caminho, dtype=str, encoding='utf-8-sig', keep_default_na=False)


def validar_chave(df, colunas, tabela):
    for coluna in colunas:
        if coluna not in df.columns:
            raise ValueError(f'{tabela}: coluna obrigatória ausente: {coluna}')
        if df[coluna].str.strip().eq('').any():
            raise ValueError(f'{tabela}: chave vazia em {coluna}')
    if df.duplicated(colunas).any():
        raise ValueError(f'{tabela}: chave duplicada em {colunas}')


@dataclass
class BaseDados:
    pasta: Path
    estabelecimentos: pd.DataFrame
    catalogo: pd.DataFrame
    templates: dict
    dicionario: pd.DataFrame
    avisos: list[str]
    hashes: dict[str, str]

    def registro(self, empresa_id, imovel_id):
        df = self.estabelecimentos
        linhas = df.loc[df.empresa_id.eq(empresa_id) & df.imovel_id.eq(imovel_id)]
        if len(linhas) != 1:
            raise ValueError('Empresa-estabelecimento não encontrado.')
        return linhas.iloc[0].to_dict()


def agregar_bens(bens, enderecos):
    """Recalcula valores ponderados; nunca aplica a probabilidade duas vezes."""
    obrigatorias = ['bem_id', 'empresa_id', 'imovel_id_referencia', 'tipo_bem',
                    'valor_cadastrado', 'probabilidade_bem_no_imovel_referencia']
    for coluna in obrigatorias:
        if coluna not in bens:
            raise ValueError(f'bens_cadastrados: coluna ausente: {coluna}')
    bens = bens.drop_duplicates().copy()
    validar_chave(bens, ['bem_id'], 'bens_cadastrados')
    pares = set(map(tuple, enderecos[CHAVES].to_numpy()))
    acumulados = {}
    for bem in bens.to_dict('records'):
        chave = (bem['empresa_id'], bem['imovel_id_referencia'])
        if chave not in pares:
            raise ValueError(f'Bem com vínculo órfão ou empresa divergente: {bem["bem_id"]}')
        a = acumulados.setdefault(chave, {
            'bens_total_referencia': 0., 'bens_ponderados': 0.,
            'equipamentos_ponderados': 0., 'equipamentos_total_referencia': 0.,
            'informatica_ponderada': 0., 'cozinha_ponderada': 0.,
            'bens_quantidade': 0, 'bens_validos': 0, 'bens_ponderacao_validos': 0,
            'bens_baixa_confianca': 0,
        })
        a['bens_quantidade'] += 1
        valor = numero(bem['valor_cadastrado'])
        prob = numero(bem['probabilidade_bem_no_imovel_referencia'])
        if bem.get('nivel_confianca_vinculo') == 'BAIXA':
            a['bens_baixa_confianca'] += 1
        if valor is None:
            continue
        a['bens_total_referencia'] += valor
        a['bens_validos'] += 1
        eletrico = bem['tipo_bem'] in TIPOS_ELETRICOS
        if eletrico:
            a['equipamentos_total_referencia'] += valor
        if prob is None or prob > 1:
            continue
        a['bens_ponderacao_validos'] += 1
        atribuido = valor * prob
        a['bens_ponderados'] += atribuido
        if eletrico:
            a['equipamentos_ponderados'] += atribuido
        if bem['tipo_bem'] == 'EQUIPAMENTO_INFORMATICA':
            a['informatica_ponderada'] += atribuido
        if bem['tipo_bem'] == 'EQUIPAMENTO_COZINHA':
            a['cozinha_ponderada'] += atribuido
    saida = []
    for (empresa, imovel), a in acumulados.items():
        n = a['bens_quantidade']
        a['confianca_bens'] = (a['bens_ponderacao_validos'] / n
                              * (1 - .5 * a['bens_baixa_confianca'] / n))
        if not a['bens_ponderacao_validos']:
            for campo in ['bens_ponderados', 'equipamentos_ponderados',
                          'informatica_ponderada', 'cozinha_ponderada']:
                a[campo] = None
        saida.append({'empresa_id': empresa, 'imovel_id': imovel, **a})
    return pd.DataFrame(saida, columns=CHAVES + list(next(iter(acumulados.values()), {})))


def carregar_base(pasta=None, enriquecimento=None, referencias=None, confirmacoes=None):
    pasta = localizar_dados(pasta)
    faltantes = [f'{n}.csv' for n in ARQUIVOS if not (pasta / f'{n}.csv').is_file()]
    if faltantes:
        raise ValueError('Arquivos ausentes: ' + ', '.join(faltantes))
    dic = ler_csv(pasta / 'dicionario_dados.csv')
    tabelas = {n: ler_csv(pasta / f'{n}.csv') for n in ARQUIVOS if n != 'dicionario_dados'}
    empresas = tabelas['empresas']
    enderecos = tabelas['enderecos_estabelecimentos']
    sinais = tabelas['sinais_financeiros_operacionais']
    territorio = tabelas['territorio']
    obrigatorias = {
        'empresas': ['empresa_id', 'grupo_atividade', 'cnae_principal', 'descricao_cnae', 'porte'],
        'enderecos_estabelecimentos': CHAVES + ['territorio_id', 'tipo_unidade',
            'municipio_real', 'uf_real', 'codigo_ibge_municipio'],
    }
    for tabela, colunas in obrigatorias.items():
        ausentes = set(colunas) - set(tabelas[tabela].columns)
        if ausentes:
            raise ValueError(f'{tabela}: colunas obrigatórias ausentes: {sorted(ausentes)}')
    validar_chave(empresas, ['empresa_id'], 'empresas')
    validar_chave(enderecos, CHAVES, 'enderecos_estabelecimentos')
    validar_chave(enderecos, ['imovel_id'], 'enderecos_estabelecimentos')
    validar_chave(sinais, CHAVES, 'sinais_financeiros_operacionais')
    validar_chave(territorio, ['territorio_id'], 'territorio')
    if not set(enderecos.empresa_id).issubset(set(empresas.empresa_id)):
        raise ValueError('Estabelecimentos com empresa inexistente.')
    if not set(map(tuple, sinais[CHAVES].to_numpy())).issubset(set(map(tuple, enderecos[CHAVES].to_numpy()))):
        raise ValueError('Sinais com empresa-estabelecimento inexistente.')
    avisos = []
    dados = enderecos.merge(empresas, on='empresa_id', validate='many_to_one')
    dados['quantidade_unidades'] = dados.groupby('empresa_id').imovel_id.transform('count')
    dados = dados.merge(sinais, on=CHAVES, how='left', validate='one_to_one', indicator=True)
    if dados['_merge'].ne('both').any():
        avisos.append('Há unidades sem sinais financeiros; a confiança será reduzida.')
    dados = dados.drop(columns='_merge')
    # Preserva o município cadastral; não infere bairro pelas coordenadas alteradas.
    extras = [c for c in territorio if c not in dados or c == 'territorio_id']
    dados = dados.merge(territorio[extras], on='territorio_id', how='left', validate='many_to_one')
    agregados = agregar_bens(tabelas['bens_cadastrados'], enderecos)
    if len(agregados):
        dados = dados.merge(agregados, on=CHAVES, how='left', validate='one_to_one')
    else:
        for campo in ['bens_ponderados', 'bens_total_referencia', 'equipamentos_ponderados',
                      'equipamentos_total_referencia', 'informatica_ponderada',
                      'cozinha_ponderada', 'confianca_bens']:
            dados[campo] = None
    fontes_lidas = {}
    # Referências públicas são locais e opcionais. Nenhuma rede durante a análise.
    pasta_ref = localizar_referencias(referencias)
    for nome, tipo in [('seguranca_municipal.csv','seguranca'),('clima_municipal.csv','clima')]:
        caminho = caminho_referencia(nome,pasta_ref)
        if caminho.exists():
            dados = incorporar_indicador(dados,caminho,tipo)
            fontes_lidas[str(caminho.resolve())] = hashlib.sha256(caminho.read_bytes()).hexdigest()
    caminho_ssp = pasta_ref/'seguranca_ssp.csv'
    if caminho_ssp.exists():
        dados = incorporar_ssp(dados,caminho_ssp)
        fontes_lidas[str(caminho_ssp.resolve())] = hashlib.sha256(caminho_ssp.read_bytes()).hexdigest()
    caminho = caminho_referencia('nr4_cnae.csv',pasta_ref)
    if caminho.exists():
        nr4 = ler_csv(caminho)
        validar_chave(nr4,['classe_cnae'],'nr4')
        for coluna in ['grau_risco_nr4','fonte_nr4','versao_nr4']:
            if coluna not in nr4:
                raise ValueError(f'Referência NR-4 sem {coluna}.')
        if nr4.grau_risco_nr4.map(numero).isna().any() or not nr4.grau_risco_nr4.isin(['1','2','3','4']).all():
            raise ValueError('Graus NR-4 devem ser inteiros de 1 a 4.')
        dados['classe_cnae'] = dados.cnae_principal.map(classe_cnae)
        dados = dados.merge(nr4,on='classe_cnae',how='left',validate='many_to_one')
        fontes_lidas[str(caminho.resolve())] = hashlib.sha256(caminho.read_bytes()).hexdigest()
    if enriquecimento:
        dados = incorporar_territorio(dados, enriquecimento)
    if confirmacoes:
        confirmado = ler_csv(confirmacoes)
        validar_chave(confirmado,CHAVES,'confirmacoes')
        permitidas = CHAVES + ['possui_vidros_confirmado','valor_vidros_reposicao_brl','funcionarios_unidade_confirmados']
        if set(confirmado.columns)-set(permitidas):
            raise ValueError('Confirmações contêm colunas não previstas.')
        if 'possui_vidros_confirmado' in confirmado and not confirmado.possui_vidros_confirmado.isin(['SIM','NAO','']).all():
            raise ValueError('Presença de vidros deve ser SIM, NAO ou vazia.')
        for c in ['valor_vidros_reposicao_brl','funcionarios_unidade_confirmados']:
            if c in confirmado:
                preenchidos=confirmado[c].ne('')
                n=confirmado.loc[preenchidos,c].map(numero)
                if n.isna().any() or (c=='funcionarios_unidade_confirmados' and any(x!=int(x) for x in n)):
                    raise ValueError(f'Confirmação numérica inválida: {c}')
        if {'possui_vidros_confirmado','valor_vidros_reposicao_brl'}<=set(confirmado):
            if (confirmado.possui_vidros_confirmado.eq('NAO') & confirmado.valor_vidros_reposicao_brl.map(numero).fillna(0).gt(0)).any():
                raise ValueError('Confirmação contraditória: ausência de vidros com valor positivo.')
        if not set(map(tuple,confirmado[CHAVES].to_numpy())).issubset(set(map(tuple,dados[CHAVES].to_numpy()))):
            raise ValueError('Confirmação para empresa-estabelecimento inexistente.')
        dados = dados.merge(confirmado,on=CHAVES,how='left',validate='one_to_one')
        fontes_lidas[str(Path(confirmacoes).resolve())] = hashlib.sha256(Path(confirmacoes).read_bytes()).hexdigest()
    for coluna, descricao in [('seguranca_da_cidade_0_1','segurança territorial'),
                              ('exposicao_climatica_0_1','exposição climática'),
                              ('grau_risco_nr4','classificação NR-4')]:
        presentes = dados[coluna].map(numero).notna() if coluna in dados else pd.Series(False,index=dados.index)
        if coluna == 'seguranca_da_cidade_0_1' and 'confianca_seguranca_0_1' in dados:
            presentes &= dados.confianca_seguranca_0_1.map(numero).fillna(0).gt(0)
        n = presentes.sum()
        if n < len(dados):
            avisos.append(f'{descricao}: {n}/{len(dados)} unidades com referência; ausências ampliam a incerteza.')
    templates = {n: tabelas[n].columns.tolist() for n in ('template_resultado_times', 'template_coberturas_times')}
    catalogo = tabelas['catalogo_coberturas_fixas_planos']
    validar_chave(catalogo, ['plano', 'cobertura_fixa'], 'catalogo')
    if set(catalogo.plano) != {'ESSENCIAL', 'PRATICO', 'TOTAL'}:
        raise ValueError('Catálogo deve conter ESSENCIAL, PRATICO e TOTAL.')
    hashes = {f'{n}.csv': hashlib.sha256((pasta / f'{n}.csv').read_bytes()).hexdigest() for n in ARQUIVOS}
    hashes.update(fontes_lidas)
    if enriquecimento:
        hashes['enriquecimento_territorial.csv'] = hashlib.sha256(Path(enriquecimento).read_bytes()).hexdigest()
    return BaseDados(pasta, dados.astype(object).where(pd.notna(dados), None),
                     catalogo, templates, dic, avisos, hashes)


def incorporar_territorio(dados, caminho):
    """Aceita indicadores externos documentados, com uma linha por município."""
    externo = ler_csv(caminho)
    obrigatorias = ['codigo_ibge_municipio', 'fonte', 'ano_referencia',
                    'granularidade', 'metodologia', 'confianca_territorial_0_1']
    for c in obrigatorias:
        if c not in externo or externo[c].str.strip().eq('').any():
            raise ValueError(f'Enriquecimento sem metadado obrigatório: {c}')
    validar_chave(externo, ['codigo_ibge_municipio'], 'enriquecimento')
    indicadores = [c for c in ['seguranca_da_cidade_0_1', 'exposicao_climatica_0_1'] if c in externo]
    if not indicadores:
        raise ValueError('Enriquecimento sem indicador territorial aceito.')
    for c in indicadores + ['confianca_territorial_0_1']:
        valores = externo[c].map(numero)
        if valores.isna().any() or valores.gt(1).any():
            raise ValueError(f'{c} deve estar entre 0 e 1.')
    if externo.granularidade.ne('MUNICIPIO').any():
        raise ValueError('Esta versão aceita enriquecimento municipal; não replica precisão de rua.')
    if not set(externo.ano_referencia.str.fullmatch(r'\d{4}')).issubset({True}):
        raise ValueError('ano_referencia deve conter o ano da observação com quatro dígitos.')
    # Compatibilidade do CSV anterior: expande metadados por indicador.
    for indicador in indicadores:
        tipo = 'seguranca' if indicador=='seguranca_da_cidade_0_1' else 'clima'
        if tipo == 'seguranca':
            dados = dados.drop(columns=['indicador_disponivel','roubo_comercio_total',
                'taxa_por_mil_estabelecimentos','estabelecimentos_referencia','referencia_taxa_por_mil',
                'regioes_fonte','sha256_arquivos','atualizado_em_utc',
                'taxa_roubo_domicilios','taxa_furto_domicilios','exposicao_bruta'],errors='ignore')
        metadados = {'fonte':f'fonte_{tipo}','ano_referencia':f'periodo_{tipo}',
            'granularidade':f'granularidade_{tipo}','metodologia':f'metodologia_{tipo}',
            'confianca_territorial_0_1':f'confianca_{tipo}_0_1'}
        parte = externo[['codigo_ibge_municipio',indicador]+list(metadados)].rename(columns=metadados)
        dados = juntar_indicador(dados,parte)
    return dados


def juntar_indicador(dados, externo):
    substituir = [c for c in externo if c in dados and c!='codigo_ibge_municipio']
    return dados.drop(columns=substituir).merge(externo,on='codigo_ibge_municipio',how='left',validate='many_to_one')


def incorporar_indicador(dados,caminho,tipo):
    externo = ler_csv(caminho)
    indicador = 'seguranca_da_cidade_0_1' if tipo=='seguranca' else 'exposicao_climatica_0_1'
    metadados = [f'fonte_{tipo}',f'periodo_{tipo}',f'granularidade_{tipo}',
                 f'metodologia_{tipo}',f'confianca_{tipo}_0_1']
    for c in ['codigo_ibge_municipio',indicador]+metadados:
        if c not in externo or externo[c].str.strip().eq('').any():
            raise ValueError(f'Referência {tipo}: campo ausente ou vazio: {c}')
    validar_chave(externo,['codigo_ibge_municipio'],tipo)
    for c in [indicador,f'confianca_{tipo}_0_1']:
        n=externo[c].map(numero)
        if n.isna().any() or n.gt(1).any():
            raise ValueError(f'{c} deve estar entre 0 e 1.')
    if externo[f'granularidade_{tipo}'].ne('MUNICIPIO').any():
        raise ValueError('Referência territorial exige granularidade municipal.')
    return juntar_indicador(dados,externo.drop(columns=['municipio'],errors='ignore'))


def incorporar_ssp(dados, caminho):
    """SSP substitui segurança apenas em municípios explicitamente presentes no arquivo."""
    externo = ler_csv(caminho)
    # Reutiliza validação de valores, chaves e metadados do formato público.
    incorporar_indicador(dados[['codigo_ibge_municipio']],caminho,'seguranca')
    for coluna in ['indicador_disponivel','roubo_comercio_total','taxa_por_mil_estabelecimentos',
                   'estabelecimentos_referencia','sha256_arquivos','atualizado_em_utc']:
        if coluna not in externo:
            raise ValueError(f'Referência SSP sem {coluna}.')
    if not externo.indicador_disponivel.isin(['SIM','NAO']).all():
        raise ValueError('Disponibilidade SSP deve ser SIM ou NAO.')
    indisponivel = externo.indicador_disponivel.eq('NAO')
    if externo.loc[indisponivel,'confianca_seguranca_0_1'].map(numero).ne(0).any():
        raise ValueError('SSP indisponível deve ter confiança zero.')
    resultado = dados.copy()
    mascara = resultado.codigo_ibge_municipio.isin(externo.codigo_ibge_municipio)
    for coluna in ['taxa_furto_domicilios','taxa_roubo_domicilios','exposicao_bruta']:
        if coluna in resultado:
            resultado.loc[mascara,coluna] = None
    referencia = externo.set_index('codigo_ibge_municipio')
    for coluna in externo:
        if coluna in ['codigo_ibge_municipio','municipio','uf']:
            continue
        if coluna not in resultado:
            resultado[coluna] = None
        resultado[coluna] = resultado[coluna].astype(object)
        resultado.loc[mascara,coluna] = resultado.loc[mascara,'codigo_ibge_municipio'].map(referencia[coluna])
    return resultado
