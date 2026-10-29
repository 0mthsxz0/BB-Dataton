"""Cruzamento IBGE + SINESP + CSV, com avaliação Mosler por estabelecimento.

Os pesos são hipóteses editáveis do projeto. Notas ausentes nunca são inferidas
do CNAE, de renda, de cidade ou do valor do bem. Não estima probabilidade.
"""
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo
import copy
import hashlib
import json
import math
import re

import pandas as pd

from .banco import crime_canonico, sigla_uf
from .indice import percentil, suavizar


CHAVES = ['empresa_id', 'imovel_id']
CRITERIOS_CSV = ['mosler_f', 'mosler_s', 'mosler_p', 'mosler_e', 'mosler_v', 'exposicao_atividade_1a5']
EVIDENCIAS = ['avaliador_mosler', 'data_avaliacao_mosler', 'evidencias_mosler']


def validar_pesos(pesos, chaves=None):
    if not isinstance(pesos, dict) or not pesos or (chaves and set(pesos) != set(chaves)):
        raise ValueError('Conjunto de pesos incompatível com o modelo.')
    valores = list(pesos.values())
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in valores):
        raise ValueError('Pesos devem ser positivos e finitos.')
    if not math.isclose(sum(valores), 1, abs_tol=1e-10):
        raise ValueError('Pesos devem somar 1; não são normalizados silenciosamente.')


def validar_config(config):
    validar_pesos(config['pesos_crimes'])
    validar_pesos(config['pesos_agressao'], {'contexto_municipal', 'exposicao_atividade_csv'})
    crimes = [crime_canonico(c) for c in config['pesos_crimes']]
    if len(set(crimes)) != len(crimes) or any(not c.startswith('roubo ') for c in crimes):
        raise ValueError('Informe subtipos de roubo distintos; não misture total e subtipos.')
    if config['minimo_municipios_contexto'] < 3:
        raise ValueError('Contexto exige ao menos três municípios completos.')
    delta = config['sensibilidade_relativa_pesos']
    if not isinstance(delta, (float, int)) or not math.isfinite(delta) or not 0 < delta < 1:
        raise ValueError('Variação de sensibilidade deve estar entre 0 e 1.')


def nota(valor):
    if valor is None or pd.isna(valor) or not str(valor).strip():
        return None
    if isinstance(valor, bool):
        raise ValueError('Notas Mosler devem ser inteiros entre 1 e 5.')
    try:
        n = float(valor)
    except (ValueError, TypeError) as exc:
        raise ValueError('Notas Mosler devem ser inteiros entre 1 e 5.') from exc
    if not math.isfinite(n) or not n.is_integer() or not 1 <= n <= 5:
        raise ValueError('Notas Mosler devem ser inteiros entre 1 e 5.')
    return int(n)


def arredondar_nota(valor):
    return int(Decimal(str(valor)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def classificar_mosler(er):
    if er is None:
        return 'indisponivel', 'indisponivel'
    if er <= 250:
        return 'muito baixo', 'baixo'
    if er <= 500:
        return 'baixo', 'baixo'
    if er <= 750:
        return 'normal', 'moderado'
    if er <= 1000:
        return 'alto', 'alto'
    return 'muito alto', 'muito alto'


def calcular_mosler(f, s, p, e, a, v):
    valores = [nota(x) for x in (f, s, p, e, a, v)]
    if None in valores:
        raise ValueError('Mosler completo exige seis notas; não presumir dados ausentes.')
    f, s, p, e, a, v = valores
    importancia, danos = f*s, p*e
    carater, produto_agressao_vulnerabilidade = importancia+danos, a*v
    er = carater*produto_agressao_vulnerabilidade
    tradicional, projeto = classificar_mosler(er)
    return {'F': f, 'S': s, 'P': p, 'E': e, 'A': a, 'V': v,
            'importancia': importancia, 'danos': danos, 'carater': carater,
            'produto_agressao_vulnerabilidade': produto_agressao_vulnerabilidade,
            'er_mosler': er, 'indice_mosler_0_100': (er-2)/1248*100,
            'faixa_mosler': tradicional, 'faixa_projeto': projeto}


def construir_contexto(con, config, fim, data_analise):
    """Uma linha municipal: denominadores IBGE e séries SINESP na mesma grade.

    A coorte é municipal, independente de quantas empresas do CSV ficam na cidade.
    Não reutiliza o antigo índice CRITIC como entrada nem adota fonte substituta.
    """
    if not re.fullmatch(r'\d{4}-\d{2}', fim):
        raise ValueError('Fim da janela deve ter formato AAAA-MM.')
    ultimo = pd.Period(fim, 'M')
    fechado = pd.Period(data_analise, 'M')-1
    if ultimo > fechado:
        raise ValueError('Use mês civil encerrado na data da análise.')
    meses = [str(m)+'-01' for m in pd.period_range(ultimo-11, ultimo, freq='M')]
    locais = pd.DataFrame([dict(r) for r in con.execute('SELECT * FROM municipios ORDER BY codigo_ibge')])
    if locais.empty:
        return pd.DataFrame(), {'inicio': meses[0][:7], 'fim': fim, 'coorte_municipal': 0, 'alertas': ['Cadastro IBGE não importado.']}
    locais = locais.set_index('codigo_ibge')
    pesos = {crime_canonico(c): w for c, w in config['pesos_crimes'].items()}
    crimes = list(pesos)
    observacoes = pd.DataFrame([dict(r) for r in con.execute(
        'SELECT * FROM ocorrencias WHERE mes BETWEEN ? AND ?', (meses[0], meses[-1]))],
        columns=['codigo_ibge', 'crime', 'mes', 'ocorrencias'])
    grade = pd.MultiIndex.from_product([locais.index, crimes], names=['codigo_ibge', 'crime'])
    agregado = observacoes[observacoes.crime.isin(crimes)].groupby(['codigo_ibge', 'crime']).agg(
        ocorrencias_12m=('ocorrencias', 'sum'), meses=('mes', 'nunique')).reindex(grade)
    contagem = agregado.meses.fillna(0).unstack()
    totais = agregado.ocorrencias_12m.unstack()
    elegivel = contagem.eq(12).all(axis=1) & locais.populacao.gt(0) & locais.ano_populacao.notna()
    elegivel &= locais.ano_populacao.le(ultimo.year)
    coorte = locais.loc[elegivel]
    detalhes = {codigo: {} for codigo in locais.index}
    percentis = pd.DataFrame(index=locais.index, columns=crimes, dtype=float)
    priors = {}
    for codigo in locais.index:
        for crime in crimes:
            detalhes[codigo][crime] = {'meses': int(contagem.loc[codigo, crime]),
                'ocorrencias_12m': int(totais.loc[codigo, crime]) if contagem.loc[codigo, crime] == 12 else None}
    if len(coorte) >= config['minimo_municipios_contexto']:
        for crime in crimes:
            taxa, peso_dado, prior = suavizar(totais.loc[coorte.index, crime], coorte.populacao)
            priors[crime] = prior
            # Sem contraste, não há posição de risco identificável para esse critério.
            if pd.Series(taxa).nunique() < 2:
                continue
            p = percentil(taxa)
            percentis.loc[coorte.index, crime] = p.to_numpy()
            for i, codigo in enumerate(coorte.index):
                detalhes[codigo][crime].update({'taxa_bruta_100mil': float(totais.loc[codigo, crime]/coorte.loc[codigo, 'populacao']*100000),
                    'taxa_suavizada_100mil': float(taxa[i]), 'peso_observacao': float(peso_dado[i]),
                    'percentil': float(p.iloc[i]), 'peso_projeto': pesos[crime]})
    # Qualquer crime sem indicador impede a combinação. Não retirar seu peso.
    contexto = percentis.mul(pd.Series(pesos)).sum(axis=1, min_count=len(crimes))
    linhas = []
    for codigo, local in locais.iterrows():
        valor = contexto.loc[codigo]
        detalhes_municipais = {'crimes': detalhes[codigo], 'percentis': {c: None if pd.isna(percentis.loc[codigo, c]) else float(percentis.loc[codigo, c]) for c in crimes}}
        linhas.append({'codigo_ibge_municipio': codigo, 'municipio_ibge': local.municipio, 'uf_ibge': local.uf,
            'populacao_ibge': local.populacao, 'ano_populacao_ibge': local.ano_populacao,
            'area_km2_ibge': local.area_km2, 'ano_area_ibge': local.ano_area,
            'densidade_hab_km2': local.populacao/local.area_km2 if pd.notna(local.populacao) and pd.notna(local.area_km2) and local.area_km2 > 0 else None,
            'contexto_roubo_0_100': None if pd.isna(valor) else float(valor),
            'completude_sinesp_0_1': float(contagem.loc[codigo].sum()/(12*len(crimes))),
            'detalhes_contexto': detalhes_municipais})
    diagnostico = {'inicio': meses[0][:7], 'fim': fim, 'coorte_municipal': len(coorte), 'priors': priors,
                  'alertas': ['Contexto relativo aos municípios com dados completos; não mede probabilidade de roubo empresarial.']}
    if contexto.notna().sum() == 0:
        diagnostico['alertas'].append('Contexto indisponível: conferir coorte, meses, denominadores e dispersão de cada crime.')
    return pd.DataFrame(linhas), diagnostico


def ler_estabelecimentos(arquivo):
    df = pd.read_csv(arquivo, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    if df.empty:
        raise ValueError('CSV sem estabelecimentos; não há registros para cruzar.')
    obrigatorias = CHAVES+['codigo_ibge_municipio']
    if not set(obrigatorias) <= set(df.columns):
        raise ValueError('CSV consolidado exige empresa_id, imovel_id e codigo_ibge_municipio.')
    for coluna in obrigatorias:
        df[coluna] = df[coluna].str.strip()
        if df[coluna].eq('').any():
            raise ValueError(f'CSV contém chave vazia: {coluna}')
    if df.duplicated(CHAVES).any():
        raise ValueError('CSV contém empresa/estabelecimento duplicado; cruzamento não pode multiplicar linhas.')
    if not df.codigo_ibge_municipio.str.fullmatch(r'\d{7}').all():
        raise ValueError('Código municipal deve conter exatamente sete dígitos.')
    return df


def avaliar_linha(linha, config, data_analise, fim):
    motivos, avisos = [], []
    notas = {}
    for coluna in CRITERIOS_CSV:
        try:
            notas[coluna] = nota(linha.get(coluna))
            if notas[coluna] is None:
                motivos.append('ausente:'+coluna)
        except ValueError:
            notas[coluna] = None
            motivos.append('invalido:'+coluna)
    for campo in EVIDENCIAS:
        if not str(linha.get(campo, '')).strip():
            motivos.append('ausente:'+campo)
    try:
        data_avaliacao = date.fromisoformat(str(linha.get('data_avaliacao_mosler', '')))
        if data_avaliacao > data_analise:
            motivos.append('avaliacao_futura')
    except ValueError:
        motivos.append('data_avaliacao_invalida')
    contexto = linha.get('contexto_roubo_0_100')
    if contexto is None or pd.isna(contexto):
        motivos.append('contexto_ibge_sinesp_indisponivel')
    if not linha.get('municipio_ibge') or pd.isna(linha.get('municipio_ibge')):
        motivos.append('municipio_sem_correspondencia_ibge')
    uf_csv = linha.get('uf_real', linha.get('uf', ''))
    if str(uf_csv).strip() and linha.get('uf_ibge') and sigla_uf(uf_csv) != linha['uf_ibge']:
        motivos.append('uf_diverge_codigo_ibge')
    ano = linha.get('ano_populacao_ibge')
    if ano is not None and pd.notna(ano) and pd.Period(fim, 'M').year-int(ano) > 2:
        avisos.append('populacao_defasada')
    if (pd.Period(data_analise, 'M')-1).ordinal-pd.Period(fim, 'M').ordinal > 3:
        avisos.append('serie_sinesp_defasada')
    pesos = config['pesos_agressao']
    a_continuo = None if motivos else pesos['contexto_municipal']*(1+4*contexto/100)+pesos['exposicao_atividade_csv']*notas['exposicao_atividade_1a5']
    calculo = calcular_mosler(notas['mosler_f'], notas['mosler_s'], notas['mosler_p'], notas['mosler_e'],
                             arredondar_nota(a_continuo), notas['mosler_v']) if a_continuo is not None else {}
    return {**calculo, 'a_continuo_1a5': a_continuo, 'motivos': motivos, 'avisos': avisos,
            'notas_csv': notas, 'status': 'PENDENTE_DADOS' if motivos else config['status']}


def avaliar_cruzamento(con, arquivo, config, fim, data_analise=None, sensibilidade=True):
    validar_config(config)
    data_analise = data_analise or datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    if isinstance(data_analise, str):
        data_analise = date.fromisoformat(data_analise)
    estabelecimentos = ler_estabelecimentos(arquivo)
    contexto, diagnostico = construir_contexto(con, config, fim, data_analise)
    if contexto.empty:
        contexto = pd.DataFrame(columns=['codigo_ibge_municipio', 'municipio_ibge', 'uf_ibge',
            'populacao_ibge', 'ano_populacao_ibge', 'area_km2_ibge', 'ano_area_ibge',
            'densidade_hab_km2', 'contexto_roubo_0_100', 'completude_sinesp_0_1', 'detalhes_contexto'])
    # As três fontes compõem cada linha. A sequência técnica de leitura não é uma prioridade entre fontes.
    reservadas = (set(contexto.columns)-{'codigo_ibge_municipio'}) & set(estabelecimentos.columns)
    if reservadas:
        raise ValueError(f'CSV usa colunas reservadas à fonte IBGE/SINESP: {sorted(reservadas)}')
    cruzado = estabelecimentos.merge(contexto, on='codigo_ibge_municipio', how='left', validate='many_to_one')
    saidas = []
    cenarios = variantes_pesos(config) if sensibilidade else []
    for linha in cruzado.to_dict('records'):
        resultado = avaliar_linha(linha, config, data_analise, fim)
        alternativos = []
        if resultado.get('er_mosler') is not None:
            for nome, alternativo in cenarios:
                alterada = dict(linha)
                # Recombina o mesmo vetor de percentis da mesma coorte; não recalibra com o CSV.
                ps = linha['detalhes_contexto']['percentis']
                alterada['contexto_roubo_0_100'] = sum(alternativo['pesos_crimes'][c]*ps[crime_canonico(c)] for c in alternativo['pesos_crimes'])
                aval = avaliar_linha(alterada, alternativo, data_analise, fim)
                alternativos.append({'cenario': nome, 'er_mosler': aval['er_mosler'], 'indice_mosler_0_100': aval['indice_mosler_0_100'], 'faixa_projeto': aval['faixa_projeto']})
        scores = [resultado['indice_mosler_0_100']]+[a['indice_mosler_0_100'] for a in alternativos] if resultado.get('er_mosler') is not None else []
        auditoria = {'versao': config['versao'], 'status': resultado['status'], 'mosler': resultado,
            'pesos_crimes': config['pesos_crimes'], 'pesos_agressao': config['pesos_agressao'],
            'contexto': linha.get('detalhes_contexto') if isinstance(linha.get('detalhes_contexto'), dict) else None,
            'sensibilidade_pesos': alternativos}
        saidas.append({**{c: linha[c] for c in CHAVES}, 'codigo_ibge_municipio': linha['codigo_ibge_municipio'],
            'municipio_ibge': linha.get('municipio_ibge'), 'uf_ibge': linha.get('uf_ibge'),
            'populacao_ibge': linha.get('populacao_ibge'), 'ano_populacao_ibge': linha.get('ano_populacao_ibge'),
            'area_km2_ibge': linha.get('area_km2_ibge'), 'densidade_hab_km2': linha.get('densidade_hab_km2'),
            'contexto_roubo_0_100': linha.get('contexto_roubo_0_100'),
            'completude_sinesp_0_1': linha.get('completude_sinesp_0_1'),
            'er_mosler': resultado.get('er_mosler'), 'indice_mosler_0_100': resultado.get('indice_mosler_0_100'),
            'faixa_mosler': resultado.get('faixa_mosler', 'indisponivel'),
            'faixa_projeto': resultado.get('faixa_projeto', 'indisponivel'), 'status': resultado['status'],
            'menor_indice_cenarios_pesos': min(scores) if scores else None,
            'maior_indice_cenarios_pesos': max(scores) if scores else None,
            'faixa_estavel_nos_cenarios': all(a['faixa_projeto'] == resultado['faixa_projeto'] for a in alternativos) if scores else None,
            'inicio': diagnostico['inicio'], 'fim': fim, 'data_analise': data_analise.isoformat(), 'auditoria': auditoria})
    # Serialização intermediária converte NaN de junções em null, sem permitir NaN em JSON.
    df = pd.DataFrame(saidas)
    df = pd.DataFrame(json.loads(df.to_json(orient='records', force_ascii=False)))
    diagnostico.update({'metodo': config, 'csv_sha256': hashlib.sha256(Path(arquivo).read_bytes()).hexdigest(),
        'data_analise': data_analise.isoformat(), 'estabelecimentos': len(df),
        'calculados': int(df.er_mosler.notna().sum()) if len(df) else 0,
        'pendentes': int(df.er_mosler.isna().sum()) if len(df) else 0,
        'fontes_banco': [dict(r) for r in con.execute('SELECT id,url,sha256,coletado_em FROM fontes ORDER BY id')],
        'rejeicoes_sinesp': con.execute('SELECT count(*) FROM rejeicoes').fetchone()[0]})
    if diagnostico['rejeicoes_sinesp']:
        diagnostico['alertas'].append('Há rejeições SINESP; revisar antes de uso operacional.')
    return df, diagnostico


def variantes_pesos(config):
    """Varia um peso por vez e renormaliza somente nos cenários identificados."""
    delta = config['sensibilidade_relativa_pesos']
    cenarios = []
    for grupo in ['pesos_crimes', 'pesos_agressao']:
        for chave in config[grupo]:
            for fator in (1-delta, 1+delta):
                novo = copy.deepcopy(config)
                novo[grupo][chave] *= fator
                total = sum(novo[grupo].values())
                novo[grupo] = {k: v/total for k, v in novo[grupo].items()}
                cenarios.append((f'{grupo}:{chave}:x{fator:g}', novo))
    return cenarios
