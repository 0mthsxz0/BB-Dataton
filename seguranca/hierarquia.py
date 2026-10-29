"""Seleção auditável de uma fonte por município, indicador e janela completa."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path

import pandas as pd

from .banco import crime_canonico, numero, registrar_fonte, normalizar
from .fontes import download


NIVEIS = {1: 'produtor_oficial', 2: 'consolidacao_oficial', 3: 'republicacao_verificada'}


def inicializar_hierarquia(con):
    # Não usa executescript, para não confirmar uma importação parcialmente validada.
    for sql in [
        '''CREATE TABLE IF NOT EXISTS hierarquia_candidatos (
            fornecedor TEXT NOT NULL, fonte_id INTEGER NOT NULL REFERENCES fontes(id),
            codigo_ibge TEXT NOT NULL REFERENCES municipios(codigo_ibge), crime TEXT NOT NULL,
            mes TEXT NOT NULL, valor INTEGER NOT NULL CHECK(valor>=0), metrica TEXT NOT NULL,
            granularidade TEXT NOT NULL, definicao TEXT NOT NULL, consolidado INTEGER NOT NULL,
            PRIMARY KEY(fornecedor,fonte_id,codigo_ibge,crime,mes))''',
        '''CREATE TABLE IF NOT EXISTS hierarquia_selecao (
            codigo_ibge TEXT NOT NULL REFERENCES municipios(codigo_ibge), crime TEXT NOT NULL,
            inicio TEXT NOT NULL, fim TEXT NOT NULL, fornecedor TEXT,
            fonte_id INTEGER REFERENCES fontes(id), definicao TEXT, status TEXT NOT NULL,
            tentativas TEXT NOT NULL, PRIMARY KEY(codigo_ibge,crime))''',
        '''CREATE TABLE IF NOT EXISTS hierarquia_vinculos (
            codigo_ibge TEXT NOT NULL, crime TEXT NOT NULL, mes TEXT NOT NULL,
            fonte_id INTEGER NOT NULL REFERENCES fontes(id),
            PRIMARY KEY(codigo_ibge,crime,mes,fonte_id))''',
        '''CREATE TABLE IF NOT EXISTS hierarquia_execucoes (
            id INTEGER PRIMARY KEY, criado_em TEXT NOT NULL, politica_sha256 TEXT NOT NULL,
            diagnostico TEXT NOT NULL)''']:
        con.execute(sql)


def validar_politica(politica):
    if politica.get('versao') != 1:
        raise ValueError('Versão de política de fontes não suportada.')
    ids, ordens = set(), set()
    for f in politica['fontes']:
        if f['id'] in ids or (f['nivel'], f['ordem']) in ordens or f['nivel'] not in NIVEIS:
            raise ValueError('Fontes exigem identificadores e prioridades únicos; nível de 1 a 3.')
        ids.add(f['id'])
        ordens.add((f['nivel'], f['ordem']))
        if f.get('validada') is not True or not f.get('metodologia_url', '').startswith('https://'):
            raise ValueError('Fonte sem revisão metodológica explícita não pode ser ativada.')
        if f['nivel'] == 3 and not re.fullmatch(r'[0-9a-f]{64}', f.get('sha256_primario', '')):
            raise ValueError('Republicação exige hash previamente conferido do original oficial.')
    indicadores = [crime_canonico(c) for c in politica['indicadores']]
    if len(indicadores) != len(set(indicadores)) or not indicadores:
        raise ValueError('Indicadores da política devem ser distintos.')


def salvar_candidatos(con, fornecedor, fonte, registros):
    vistos, preparados = set(), []
    cadastro = {r[0] for r in con.execute('SELECT codigo_ibge FROM municipios')}
    for r in registros:
        codigo, crime = str(r['codigo_ibge']), crime_canonico(r['crime'])
        mes = pd.Period(r['mes'], freq='M').strftime('%Y-%m-01')
        if codigo not in cadastro or mes >= datetime.now(timezone.utc).strftime('%Y-%m-01'):
            raise ValueError('Candidato com código IBGE desconhecido ou mês não encerrado.')
        n = numero(r['valor'], inteiro=True)
        if n is None:
            continue  # Ausência não é zero.
        chave = (codigo, crime, mes)
        if chave in vistos:
            raise ValueError(f'Chave repetida no fornecedor {fornecedor}: {chave}')
        vistos.add(chave)
        preparados.append((fornecedor, fonte, *chave, n, r['metrica'],
                            r['granularidade'], r['definicao'], int(r['consolidado'])))
    con.execute('DELETE FROM hierarquia_candidatos WHERE fornecedor=? AND fonte_id=?', (fornecedor, fonte))
    con.executemany('INSERT INTO hierarquia_candidatos VALUES(?,?,?,?,?,?,?,?,?,?)', preparados)
    return len(preparados)


def carregar_isp_rj(con, f, raiz, ano, atualizar):
    arquivo, dicionario = raiz/f['arquivo'], raiz/f['dicionario_arquivo']
    download(f['url'], arquivo, atualizar)
    download(f['dicionario_url'], dicionario, atualizar)
    bruto = pd.read_excel(dicionario, header=None).fillna('')
    unidades = {str(r.iloc[0]).strip(): normalizar(r.iloc[2]) for _, r in bruto.iterrows()}
    mapa = {'roubo_veiculo': 'Roubo de veículo', 'roubo_carga': 'Roubo de carga',
            'roubo_comercio': 'Roubo em comércio', 'roubo_banco': 'Roubo a banco'}
    if any(unidades.get(c) != 'caso' for c in mapa) or unidades.get('latrocinio') != 'vitima':
        raise ValueError('Dicionário ISP-RJ mudou as unidades esperadas; revisar adaptador.')
    dados = pd.read_csv(arquivo, sep=';', encoding='latin1', dtype=str, keep_default_na=False)
    if not {'fmun_cod', 'fmun', 'ano', 'mes', 'fase', *mapa} <= set(dados.columns):
        raise ValueError('Layout ISP-RJ sem campos esperados.')
    dados = dados[dados.ano.eq(str(ano))]
    if dados.empty:
        raise ValueError('ISP-RJ sem o ano solicitado.')
    cadastro = {r['codigo_ibge']: dict(r) for r in con.execute('SELECT * FROM municipios WHERE uf=?', ('RJ',))}
    registros = []
    for r in dados.to_dict('records'):
        local = cadastro.get(r['fmun_cod'])
        if local is None or normalizar(local['municipio']) != normalizar(r['fmun']):
            raise ValueError('Código/nome municipal ISP-RJ divergente do cadastro IBGE.')
        mes = numero(r['mes'], inteiro=True)
        if mes is None or not 1 <= mes <= 12:
            raise ValueError('Mês ISP-RJ inválido.')
        for coluna, crime in mapa.items():
            registros.append({'codigo_ibge': r['fmun_cod'], 'crime': crime,
                'mes': f'{ano}-{mes:02d}', 'valor': r[coluna], 'metrica': 'ocorrencias',
                'granularidade': 'municipio', 'definicao': 'isp_rj:'+coluna+':casos:v1',
                'consolidado': r['fase'] in ('2', '3')})
    dic_id = registrar_fonte(con, dicionario, f['dicionario_url'])
    fonte = registrar_fonte(con, arquivo, f['url'], {'adaptador': 'isp_rj', 'ano': ano,
                              'dicionario_fonte_id': dic_id, 'metodologia_url': f['metodologia_url']})
    salvar_candidatos(con, f['id'], fonte, registros)
    return fonte


def carregar_csv(con, f, raiz, ano, atualizar):
    """Formato de troca explícito para novos adaptadores revisados, sem inferência de colunas."""
    arquivo = raiz/f['arquivo']
    meta = download(f['url'], arquivo, atualizar)
    if f['nivel'] == 3 and meta['sha256'] != f['sha256_primario']:
        raise ValueError('Republicação não coincide com o original oficial revisado.')
    df = pd.read_csv(arquivo, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    campos = {'codigo_ibge', 'crime', 'mes', 'valor', 'metrica', 'granularidade', 'definicao', 'consolidado'}
    if not campos <= set(df.columns):
        raise ValueError('CSV normalizado sem campos do contrato de fontes.')
    if not df.consolidado.isin(['SIM', 'NAO']).all():
        raise ValueError('Consolidação exige SIM/NAO explícitos.')
    df = df[df.mes.str.startswith(str(ano)+'-')].copy()
    df['consolidado'] = df.consolidado.eq('SIM')
    fonte = registrar_fonte(con, arquivo, f['url'], {'adaptador': 'csv_normalizado', 'ano': ano})
    salvar_candidatos(con, f['id'], fonte, df.to_dict('records'))
    return fonte


def carregar_ssp_rs(con, f, raiz, ano, atualizar):
    arquivo = raiz/f['arquivo']
    download(f['url'], arquivo, atualizar)
    meses = 'JAN FEV MAR ABR MAI JUN JUL AGO SET OUT NOV DEZ'.split()
    # Há formatação residual até a coluna XFD na publicação; ler apenas o contrato real.
    folhas = pd.read_excel(arquivo, sheet_name=meses, header=None, usecols=range(16), dtype=object)
    cadastro = {normalizar(r['municipio']): r['codigo_ibge']
                for r in con.execute('SELECT municipio,codigo_ibge FROM municipios WHERE uf=?', ('RS',))}
    registros, desconhecidos = [], set()
    for mes, nome in enumerate(meses, 1):
        df = folhas[nome]
        headers = [i for i in range(min(20, len(df))) if normalizar(df.iloc[i, 0]) == 'municipios']
        if len(headers) != 1:
            raise ValueError(f'Cabeçalho municipal SSP-RS não reconhecido: {nome}')
        cab = headers[0]
        if str(ano) not in ' '.join(str(v) for v in df.iloc[:cab, 0]):
            raise ValueError('SSP-RS: ano da planilha diferente do solicitado.')
        cols = {normalizar(v): i for i, v in enumerate(df.iloc[cab])}
        if not {'latrocinio', 'roubo de veiculo', 'vitimas de latrocinio'} <= set(cols):
            raise ValueError('SSP-RS: não é possível separar ocorrências e vítimas.')
        totais = [i for i in range(cab+1, len(df)) if normalizar(df.iloc[i, 0]) == 'total rs']
        if len(totais) != 1:
            raise ValueError('SSP-RS sem uma única linha de total estadual.')
        corpo = df.iloc[cab+1:totais[0]]
        if len(corpo) != 497 or corpo.iloc[:, 0].map(normalizar).duplicated().any():
            raise ValueError('SSP-RS: recorte municipal mudou; revisar cobertura e layout.')
        for rotulo in ('roubo de veiculo', 'latrocinio'):
            valores = [numero(v, inteiro=True) for v in corpo.iloc[:, cols[rotulo]]]
            if sum(v for v in valores if v is not None) != numero(df.iloc[totais[0], cols[rotulo]], inteiro=True):
                raise ValueError('SSP-RS: municípios não reconciliam com o total publicado.')
        for _, r in corpo.iterrows():
            codigo = cadastro.get(normalizar(r.iloc[0]))
            if codigo is None:
                desconhecidos.add(str(r.iloc[0]))
                continue  # Grafias ficam na auditoria; não aplicar aproximação automática.
            for rotulo, crime in [('roubo de veiculo', 'Roubo de veículo'),
                                  ('latrocinio', 'Roubo seguido de morte (latrocínio)')]:
                registros.append({'codigo_ibge': codigo, 'crime': crime,
                    'mes': f'{ano}-{mes:02d}', 'valor': r.iloc[cols[rotulo]],
                    'metrica': 'ocorrencias', 'granularidade': 'municipio',
                    'definicao': 'ssp_rs:'+rotulo+':ocorrencias:v1', 'consolidado': True})
    fonte = registrar_fonte(con, arquivo, f['url'], {'adaptador': 'ssp_rs', 'ano': ano,
                 'metodologia_url': f['metodologia_url'], 'nomes_sem_correspondencia': sorted(desconhecidos),
                 'unidade': 'Ocorrências de fato consumado; coluna de vítimas separada e não utilizada.'})
    salvar_candidatos(con, f['id'], fonte, registros)
    return fonte


def carregar_vde(con, f, raiz, ano, atualizar):
    # O VDE anual já é preservado/auditado pelo seu importador estrito.
    arquivo = raiz/f['arquivo']
    download(f['url'], arquivo, atualizar)
    fonte = registrar_fonte(con, arquivo, f['url'])
    if not con.execute('SELECT 1 FROM sqlite_master WHERE name=?', ('vde_registros',)).fetchone():
        raise ValueError('Importe/audite primeiro o VDE anual com importar-vde.')
    registros = [{'codigo_ibge': r['codigo_ibge'], 'crime': r['crime'], 'mes': r['mes'],
                  'valor': r['valor'], 'metrica': r['metrica'], 'granularidade': 'municipio',
                  'definicao': 'sinesp:'+r['crime']+':ocorrencias:v1', 'consolidado': True}
                 for r in con.execute('''SELECT * FROM vde_registros WHERE fonte_id=?
                     AND status IN ('ocorrencia_municipal','vitimas_nao_sao_ocorrencias') AND mes LIKE ?''',
                                      (fonte, f'{ano}-%'))]
    # Não importar automaticamente um arquivo novo sob uma auditoria antiga.
    if not con.execute('SELECT 1 FROM vde_registros WHERE fonte_id=? LIMIT 1', (fonte,)).fetchone():
        raise ValueError('Snapshot VDE sem auditoria desta versão; execute importar-vde.')
    salvar_candidatos(con, f['id'], fonte, registros)
    return fonte


def publicar(con, escolhas):
    """Troca somente vínculos geridos pela hierarquia; dados legados conflitantes abortam."""
    for r in con.execute('SELECT * FROM hierarquia_vinculos').fetchall():
        chave = (r['codigo_ibge'], r['crime'], r['mes'])
        con.execute('DELETE FROM ocorrencia_fontes WHERE codigo_ibge=? AND crime=? AND mes=? AND fonte_id=?', (*chave, r['fonte_id']))
        if not con.execute('SELECT 1 FROM ocorrencia_fontes WHERE codigo_ibge=? AND crime=? AND mes=?', chave).fetchone():
            con.execute('DELETE FROM ocorrencias WHERE codigo_ibge=? AND crime=? AND mes=?', chave)
    con.execute('DELETE FROM hierarquia_vinculos')
    for r in escolhas:
        chave = (r['codigo_ibge'], r['crime'], r['mes'])
        antigo = con.execute('SELECT ocorrencias FROM ocorrencias WHERE codigo_ibge=? AND crime=? AND mes=?', chave).fetchone()
        if antigo and antigo[0] != r['valor']:
            raise RuntimeError(f'Fonte legada conflitante para {chave}; transação revertida, revisão necessária.')
        con.execute('INSERT OR IGNORE INTO ocorrencias VALUES(?,?,?,?)', (*chave, r['valor']))
        con.execute('INSERT OR IGNORE INTO ocorrencia_fontes VALUES(?,?,?,?)', (*chave, r['fonte_id']))
        con.execute('INSERT INTO hierarquia_vinculos VALUES(?,?,?,?)', (*chave, r['fonte_id']))
    con.execute('DELETE FROM indices')


def resolver(con, politica, fontes_ativas, fim, erros=None):
    validar_politica(politica)
    inicializar_hierarquia(con)
    ultimo = pd.Period(fim, 'M')
    if ultimo >= pd.Timestamp.now(tz='UTC').tz_localize(None).to_period('M'):
        raise ValueError('Janela da hierarquia deve terminar em mês encerrado.')
    meses = [p.strftime('%Y-%m-01') for p in pd.period_range(ultimo-11, ultimo, freq='M')]
    erros = erros or {}
    fontes = sorted(politica['fontes'], key=lambda f: (f['nivel'], f['ordem']))
    candidatos = defaultdict(list)
    for r in con.execute('SELECT * FROM hierarquia_candidatos WHERE mes BETWEEN ? AND ?', (meses[0], meses[-1])):
        if fontes_ativas.get(r['fornecedor']) == r['fonte_id']:
            candidatos[(r['fornecedor'], r['codigo_ibge'], r['crime'])].append(dict(r))
    escolhas, decisoes, divergencias = [], [], []
    for local in con.execute('SELECT codigo_ibge,uf FROM municipios ORDER BY codigo_ibge'):
        for nome, contrato in politica['indicadores'].items():
            crime = crime_canonico(nome)
            tentativas, eleita = [], None
            for f in fontes:
                if f.get('ufs') and local['uf'] not in f['ufs']:
                    continue
                serie = candidatos.get((f['id'], local['codigo_ibge'], crime), [])
                motivo = ('falha_coleta_ou_validacao' if f['id'] in erros else
                    'fonte_nao_carregada' if f['id'] not in fontes_ativas else
                    'sem_serie_municipal_compativel' if not serie else
                    'unidade_ou_granularidade_incompativel' if any(r['metrica'] != 'ocorrencias' or r['granularidade'] != 'municipio' for r in serie) else
                    'definicao_nao_aprovada' if any(r['definicao'] not in contrato['definicoes'] for r in serie) else
                    'definicao_muda_na_serie' if len({r['definicao'] for r in serie}) != 1 else
                    'dados_nao_consolidados' if not all(r['consolidado'] for r in serie) else
                    'serie_incompleta' if {r['mes'] for r in serie} != set(meses) else '')
                if motivo:
                    tentativas.append({'fonte': f['id'], 'nivel': f['nivel'], 'motivo': motivo,
                                        'meses_disponiveis': len(serie)})
                    continue
                if eleita is None:
                    eleita = (f, serie)
                    tentativas.append({'fonte': f['id'], 'nivel': f['nivel'], 'motivo': 'selecionada', 'meses_disponiveis': 12})
                else:
                    atual = {r['mes']: r['valor'] for r in eleita[1]}
                    diferentes = [r['mes'][:7] for r in serie if atual[r['mes']] != r['valor']]
                    if diferentes:
                        divergencias.append({'codigo_ibge': local['codigo_ibge'], 'crime': crime,
                            'preferida': eleita[0]['id'], 'alternativa': f['id'], 'meses_divergentes': diferentes})
                    tentativas.append({'fonte': f['id'], 'nivel': f['nivel'], 'motivo': 'prioridade_inferior', 'meses_disponiveis': 12})
            f, serie = eleita if eleita else ({}, [])
            escolhas.extend(serie)
            decisoes.append({'codigo_ibge': local['codigo_ibge'], 'crime': crime, 'inicio': meses[0][:7], 'fim': str(ultimo),
                'fornecedor': f.get('id'), 'fonte_id': fontes_ativas.get(f.get('id')),
                'definicao': serie[0]['definicao'] if serie else None,
                'status': 'selecionada' if serie else 'fontes_esgotadas', 'tentativas': tentativas})
    publicar(con, escolhas)
    con.execute('DELETE FROM hierarquia_selecao')
    con.executemany('INSERT INTO hierarquia_selecao VALUES(?,?,?,?,?,?,?,?,?)',
        [(r['codigo_ibge'], r['crime'], r['inicio'], r['fim'], r['fornecedor'], r['fonte_id'],
          r['definicao'], r['status'], json.dumps(r['tentativas'], ensure_ascii=False)) for r in decisoes])
    selecionadas = [r for r in decisoes if r['status'] == 'selecionada']
    resumo = {'politica_versao': politica['versao'], 'inicio': meses[0][:7], 'fim': str(ultimo),
        'series_solicitadas': len(decisoes), 'series_selecionadas': len(selecionadas),
        'series_sem_fonte': len(decisoes)-len(selecionadas), 'observacoes_publicadas': len(escolhas),
        'fontes_utilizadas': pd.Series([r['fornecedor'] for r in selecionadas]).value_counts().to_dict(),
        'erros_fontes': erros, 'divergencias': divergencias,
        'limite': 'Hierarquia é política de preferência documentada, não probabilidade de acerto. Sem fonte compatível, mantém lacuna.'}
    resumo['fontes_avaliadas'] = [
        {'id': f['id'], 'nivel': f['nivel'], 'ordem': f['ordem'],
         'snapshot': dict(con.execute('SELECT url,sha256,coletado_em FROM fontes WHERE id=?',
                                      (fontes_ativas[f['id']],)).fetchone()) if f['id'] in fontes_ativas else None}
        for f in fontes]
    digest = hashlib.sha256(json.dumps(politica, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    con.execute('INSERT INTO hierarquia_execucoes VALUES(NULL,?,?,?)',
                (datetime.now(timezone.utc).isoformat(), digest, json.dumps(resumo, ensure_ascii=False)))
    return resumo, decisoes


def atualizar_hierarquia(con, politica, raiz, fim, saida, atualizar=False):
    validar_politica(politica)
    inicializar_hierarquia(con)
    ano = pd.Period(fim, 'M').year
    if not str(fim).endswith('-12'):
        raise ValueError('Os adaptadores desta edição exigem ano civil completo, fim AAAA-12.')
    ativos, erros = {}, {}
    adaptadores = {'isp_rj': carregar_isp_rj, 'ssp_rs': carregar_ssp_rs,
                  'vde_auditado': carregar_vde, 'csv_normalizado': carregar_csv}
    for f in sorted(politica['fontes'], key=lambda f: (f['nivel'], f['ordem'])):
        con.execute('SAVEPOINT fornecedor')
        try:
            if f['adaptador'] not in adaptadores:
                raise ValueError('Adaptador ainda não validado para esta fonte.')
            fonte = adaptadores[f['adaptador']](con, f, Path(raiz), ano, atualizar)
            if f['nivel'] == 3 and con.execute('SELECT sha256 FROM fontes WHERE id=?', (fonte,)).fetchone()[0] != f['sha256_primario']:
                raise ValueError('Republicação diverge do hash oficial revisado.')
            ativos[f['id']] = fonte
        except Exception as exc:
            con.execute('ROLLBACK TO fornecedor')
            erros[f['id']] = f'{type(exc).__name__}: {str(exc)[:300]}'
        finally:
            con.execute('RELEASE fornecedor')
    resumo, decisoes = resolver(con, politica, ativos, fim, erros)
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    (saida/'diagnostico_hierarquia.json').write_text(json.dumps(resumo, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (saida/'decisoes_fontes.jsonl').open('w', encoding='utf-8') as f:
        for r in decisoes:
            f.write(json.dumps(r, ensure_ascii=False)+'\n')
    linhas = [dict(r) for r in con.execute('''SELECT o.codigo_ibge,m.municipio,m.uf,o.crime,o.mes,
        o.ocorrencias,h.fornecedor,h.definicao,f.url,f.sha256
        FROM hierarquia_vinculos v JOIN ocorrencias o USING(codigo_ibge,crime,mes)
        JOIN municipios m USING(codigo_ibge)
        JOIN hierarquia_selecao h ON h.codigo_ibge=o.codigo_ibge AND h.crime=o.crime AND h.fonte_id=v.fonte_id
        JOIN fontes f ON f.id=v.fonte_id ORDER BY o.codigo_ibge,o.crime,o.mes''')]
    campos = ['codigo_ibge','municipio','uf','crime','mes','ocorrencias','fornecedor','definicao','url','sha256']
    pd.DataFrame(linhas, columns=campos).to_csv(saida/'series_municipais_selecionadas.csv', index=False, encoding='utf-8-sig')
    manifesto = {'politica': politica, 'fontes_avaliadas': resumo['fontes_avaliadas'],
        'arquivos_sha256': {nome: hashlib.sha256((saida/nome).read_bytes()).hexdigest()
                           for nome in ['diagnostico_hierarquia.json','decisoes_fontes.jsonl','series_municipais_selecionadas.csv']}}
    (saida/'manifesto_hierarquia.json').write_text(json.dumps(manifesto, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return resumo
