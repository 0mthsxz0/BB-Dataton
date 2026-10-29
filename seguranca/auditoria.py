"""Auditoria local da cobertura sem divulgar endereços ou completar séries ausentes."""
import hashlib
import json
from pathlib import Path

import pandas as pd

from .banco import normalizar


def auditar(con, estabelecimentos, saida):
    arquivo, saida = Path(estabelecimentos), Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    dados = pd.read_csv(arquivo, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    if dados.empty:
        raise ValueError('Arquivo de estabelecimentos vazio; não há denominador de cobertura.')
    obrigatorias = ['empresa_id', 'imovel_id', 'codigo_ibge_municipio', 'municipio_real', 'uf_real']
    if not set(obrigatorias) <= set(dados.columns):
        raise ValueError('Estabelecimentos: faltam identificadores e/ou município/UF/código IBGE.')
    dados = dados[obrigatorias].copy()
    duplicadas = dados.duplicated(['empresa_id', 'imovel_id'], keep=False)
    cadastro = {r['codigo_ibge']: dict(r) for r in con.execute('SELECT * FROM consulta_municipal')}
    indicadores = {}
    if con.execute('SELECT 1 FROM sqlite_master WHERE name=?', ('hierarquia_selecao',)).fetchone():
        for r in con.execute('SELECT codigo_ibge,crime FROM hierarquia_selecao WHERE status=?', ('selecionada',)):
            indicadores.setdefault(r['codigo_ibge'], set()).add(r['crime'])
    registros = []
    for pos, r in enumerate(dados.to_dict('records')):
        local = cadastro.get(r['codigo_ibge_municipio'])
        motivo = ('chave_duplicada' if duplicadas.iloc[pos] else
                  'identificador_vazio' if not r['empresa_id'] or not r['imovel_id'] else
                  'codigo_ibge_sem_correspondencia' if local is None else
                  'uf_divergente' if r['uf_real'] != local['uf'] else
                  'municipio_divergente' if normalizar(r['municipio_real']) != normalizar(local['municipio']) else '')
        indice = local['indice_roubo_0_100'] if local and not motivo else None
        disponiveis = indicadores.get(r['codigo_ibge_municipio'], set()) if not motivo else set()
        registros.append({'empresa_id': r['empresa_id'], 'imovel_id': r['imovel_id'],
                          'codigo_ibge': r['codigo_ibge_municipio'], 'uf': r['uf_real'],
                          'correspondencia_ibge': not bool(motivo), 'motivo': motivo,
                          'com_indice': indice is not None, 'indice_contextual_0_100': indice,
                          'com_algum_indicador': bool(disponiveis),
                          'com_roubo_comercio': 'roubo em comercio' in disponiveis,
                          'indicadores_disponiveis': '|'.join(sorted(disponiveis))})
    resultado = pd.DataFrame(registros)
    cobertura = resultado.groupby('uf', sort=True).agg(
        estabelecimentos=('imovel_id', 'size'),
        correspondencia_ibge=('correspondencia_ibge', 'sum'), com_indice=('com_indice', 'sum'),
        com_algum_indicador=('com_algum_indicador', 'sum'), com_roubo_comercio=('com_roubo_comercio', 'sum')).reset_index()
    cobertura['cobertura_indice_0_1'] = cobertura.com_indice / cobertura.estabelecimentos
    # A associação existe apenas em memória e nas saídas da auditoria do consumidor.
    # O banco de segurança armazena somente fontes/indicadores públicos.
    digest = hashlib.sha256(arquivo.read_bytes()).hexdigest()
    integridade = con.execute('PRAGMA integrity_check').fetchone()[0]
    duplicacoes = con.execute('''SELECT count(*) FROM (
        SELECT codigo_ibge,crime,mes FROM ocorrencias GROUP BY 1,2,3 HAVING count(*)>1)''').fetchone()[0]
    execucao = con.execute('SELECT diagnostico FROM execucoes ORDER BY id DESC LIMIT 1').fetchone()
    diagnostico = json.loads(execucao[0]) if execucao else {}
    if diagnostico:
        meses = [str(p) for p in pd.period_range(diagnostico['inicio'], diagnostico['fim'], freq='M')]
        presentes = {}
        for r in con.execute('SELECT codigo_ibge,crime,mes FROM ocorrencias WHERE mes>=? AND mes<=?',
                             (meses[0]+'-01', meses[-1]+'-01')):
            presentes.setdefault((r['codigo_ibge'], r['crime']), set()).add(r['mes'][:7])
        lacunas = [{'codigo_ibge': codigo, 'uf': local['uf'], 'crime': crime,
                    'meses_presentes': len(presentes.get((codigo, crime), set())),
                    'meses_ausentes': '|'.join(m for m in meses if m not in presentes.get((codigo, crime), set()))}
                   for codigo, local in cadastro.items() for crime in diagnostico['crimes']]
        pd.DataFrame(lacunas).to_csv(saida/'lacunas_municipio_crime.csv', index=False, encoding='utf-8-sig')
    resultado.to_csv(saida/'estabelecimentos_indice.csv', index=False, encoding='utf-8-sig')
    resultado.loc[~resultado.correspondencia_ibge].to_csv(saida/'estabelecimentos_revisar.csv', index=False, encoding='utf-8-sig')
    cobertura.to_csv(saida/'cobertura_estabelecimentos_uf.csv', index=False, encoding='utf-8-sig')
    resumo = {'sha256_estabelecimentos': digest, 'estabelecimentos': len(dados),
              'linhas_em_chaves_duplicadas': int(duplicadas.sum()),
              'correspondencia_ibge': int(resultado.correspondencia_ibge.sum()),
              'municipios_distintos': int(resultado.codigo_ibge.nunique()),
              'com_indice': int(resultado.com_indice.sum()),
              'com_algum_indicador': int(resultado.com_algum_indicador.sum()),
              'com_roubo_comercio': int(resultado.com_roubo_comercio.sum()),
              'cobertura_indice_0_1': float(resultado.com_indice.mean()) if len(resultado) else None,
              'motivos_revisao': resultado.loc[resultado.motivo.ne(''), 'motivo'].value_counts().to_dict(),
              'integridade_sqlite': integridade, 'violacoes_fk': len(con.execute('PRAGMA foreign_key_check').fetchall()),
              'chaves_mensais_duplicadas_banco': duplicacoes,
              'pesos_critic': diagnostico.get('pesos_critic', {}),
              'municipios_com_indice': con.execute('SELECT count(*) FROM indices WHERE indice_roubo_0_100 IS NOT NULL').fetchone()[0],
              'cobertura_uf': cobertura.to_dict('records'),
              'limite': 'Correspondência IBGE não é cobertura do índice. Universo de clientes é o pacote local do desafio.'}
    resumo['arquivos_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in saida.glob('*.csv')}
    (saida/'auditoria.json').write_text(json.dumps(resumo, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return resumo
