"""Suavização empírica Gamma-Poisson e ponderação CRITIC, sem pesos manuais."""
from datetime import datetime, timezone
import json
import re

import numpy as np
import pandas as pd

from .banco import crime_canonico


def percentil(serie):
    serie = pd.Series(serie, dtype=float)
    if len(serie) < 2:
        raise ValueError('Percentil exige ao menos dois municípios.')
    return (serie.rank(method='average') - 1) / (len(serie) - 1) * 100


def suavizar(contagens, populacao):
    """Prior estimado na coorte completa, por momentos do modelo Poisson-Gamma.

    E[N_i]=e_i*mu; Var(N_i)=e_i*mu+e_i²*tau², e_i=pop_i/100000.
    tau²=max(0, sum((N_i-e_i*mu)²-e_i*mu)/sum(e_i²)).
    """
    contagens, e = np.asarray(contagens, dtype=float), np.asarray(populacao, dtype=float) / 100_000
    if len(e) < 2 or not np.isfinite(e).all() or (e <= 0).any():
        raise ValueError('Suavização requer exposições positivas e finitas.')
    if not np.isfinite(contagens).all() or (contagens < 0).any():
        raise ValueError('Contagens inválidas.')
    mu = contagens.sum() / e.sum()
    tau2 = max(0., float((((contagens-e*mu)**2-e*mu).sum()) / (e**2).sum()))
    if mu == 0 or tau2 == 0:
        return np.full(len(e), mu), np.zeros(len(e)), {'media_nacional': float(mu), 'variancia_prior': tau2, 'beta': None}
    beta = mu / tau2
    peso_dado = e / (e + beta)
    return ((contagens + mu*beta) / (e + beta), peso_dado,
            {'media_nacional': float(mu), 'variancia_prior': tau2, 'beta': float(beta)})


def pesos_critic(matriz):
    """CRITIC de Diakoulaki et al. (1995), correlação de Pearson sem módulo."""
    matriz = pd.DataFrame(matriz, dtype=float)
    desvios = matriz.std(ddof=1)
    ativas = desvios[desvios > 1e-10].index
    if len(ativas) == 0:
        raise ValueError('Nenhum crime com dispersão: CRITIC não identifica pesos.')
    if len(ativas) == 1:
        return {c: float(c == ativas[0]) for c in matriz.columns}
    corr = matriz[ativas].corr().clip(-1, 1)
    informacao = desvios[ativas] * (1-corr).sum()
    if not np.isfinite(informacao).all() or informacao.sum() <= 1e-10:
        raise ValueError('Critérios perfeitamente redundantes: CRITIC degenerado; não usar pesos inventados.')
    pesos = informacao / informacao.sum()
    return {c: float(pesos.get(c, 0)) for c in matriz.columns}


def faixa(indice):
    if indice is None:
        return 'indisponivel'
    return 'baixo' if indice < 25 else 'moderado' if indice < 50 else 'alto' if indice < 75 else 'muito alto'


def gerar_indice(con, crimes, fim=None, minimo_municipios=30):
    crimes = [crime_canonico(c) for c in crimes]
    if not crimes or len(set(crimes)) != len(crimes):
        raise ValueError('Informe crimes distintos para o índice.')
    if any(not c.startswith('roubo ') and c != 'roubo' for c in crimes):
        raise ValueError('Índice de roubo só admite naturezas de roubo; não confundir com furto ou homicídio.')
    if 'roubo' in crimes and len(crimes) > 1:
        raise ValueError('Não misture agregado de roubo com subtipos: possível dupla contagem.')
    if minimo_municipios < 3:
        raise ValueError('São necessários ao menos três municípios para estimar a coorte.')
    lugares = pd.DataFrame([dict(r) for r in con.execute('SELECT * FROM municipios ORDER BY codigo_ibge')])
    if lugares.empty:
        raise ValueError('Cadastro municipal vazio.')
    valores = pd.DataFrame([dict(r) for r in con.execute('SELECT * FROM ocorrencias')])
    if valores.empty:
        raise ValueError('Base sem observações SINESP; não gerar índices fictícios.')
    selecionados = valores[valores.crime.isin(crimes)].copy()
    faltantes = sorted(set(crimes)-set(selecionados.crime))
    if faltantes:
        raise ValueError(f'Crimes selecionados ausentes da fonte: {faltantes}')
    if fim is not None and not re.fullmatch(r'\d{4}-\d{2}', fim):
        raise ValueError('Informe fim no formato AAAA-MM.')
    ultimo_fechado = pd.Timestamp.now(tz='UTC').tz_localize(None).to_period('M')-1
    ultimo = pd.Period(fim, 'M') if fim else pd.Period(selecionados.mes.max(), 'M')
    if ultimo > ultimo_fechado:
        raise ValueError('Fim deve ser um mês civil já encerrado.')
    meses = [str(p)+'-01' for p in pd.period_range(ultimo-11, ultimo, freq='M')]
    janela = selecionados[selecionados.mes.isin(meses)]
    grade = pd.MultiIndex.from_product([lugares.codigo_ibge, crimes], names=['codigo_ibge', 'crime'])
    agregado = janela.groupby(['codigo_ibge', 'crime']).agg(total=('ocorrencias', 'sum'), meses=('mes', 'nunique')).reindex(grade)
    contagem_meses = agregado['meses'].fillna(0).unstack()
    totais = agregado['total'].unstack()
    lugares = lugares.set_index('codigo_ibge')
    completos = contagem_meses.eq(12).all(axis=1)
    elegiveis = completos & lugares.populacao.notna() & (lugares.populacao > 0)
    coorte = lugares.loc[elegiveis]
    diagnostico = {
        'versao_metodo': 1, 'inicio': meses[0][:7], 'fim': str(ultimo),
        'crimes': crimes, 'municipios_cadastro': len(lugares), 'municipios_elegiveis': len(coorte),
        'minimo_municipios': minimo_municipios, 'pesos_critic': {}, 'suavizacao': {},
        'rejeicoes_importacao': con.execute('SELECT count(*) FROM rejeicoes').fetchone()[0],
        'alertas': [],
    }
    escores = pd.Series(dtype=float)
    detalhes_crimes = {}
    if len(coorte) < minimo_municipios:
        diagnostico['alertas'].append('Coorte completa insuficiente; nenhum índice foi calculado.')
    else:
        percentis = {}
        for crime in crimes:
            bruta = totais.loc[coorte.index, crime] / coorte.populacao * 100_000
            taxa, peso, prior = suavizar(totais.loc[coorte.index, crime], coorte.populacao)
            suavizada = pd.Series(taxa, index=coorte.index)
            p = percentil(suavizada)
            p.index = coorte.index
            percentis[crime] = p
            diagnostico['suavizacao'][crime] = prior
            for pos, codigo in enumerate(coorte.index):
                detalhes_crimes.setdefault(codigo, {})[crime] = {
                    'ocorrencias_12m': int(totais.loc[codigo, crime]),
                    'taxa_bruta_100mil': float(bruta.loc[codigo]),
                    'taxa_suavizada_100mil': float(taxa[pos]),
                    'peso_observacao': float(peso[pos]), 'percentil': float(p.loc[codigo]),
                }
        matriz = pd.DataFrame(percentis)
        try:
            pesos = pesos_critic(matriz)
            escores = matriz.mul(pd.Series(pesos)).sum(axis=1).clip(0, 100)
            diagnostico['pesos_critic'] = pesos
        except ValueError as exc:
            diagnostico['alertas'].append(str(exc))
    idade_meses = int(ultimo_fechado.ordinal-ultimo.ordinal)
    if idade_meses > 3:
        diagnostico['alertas'].append(f'Série termina há {idade_meses} meses; não representa os últimos 12 meses atuais.')
    if diagnostico['rejeicoes_importacao']:
        diagnostico['alertas'].append('Há linhas rejeitadas: revisar antes de usar o ranking.')
    resultado = []
    for codigo, local in lugares.iterrows():
        score = float(escores.loc[codigo]) if codigo in escores.index else None
        observados = int(contagem_meses.loc[codigo].sum())
        completude = observados / (12*len(crimes))
        motivos = []
        if not completos.loc[codigo]:
            motivos.append('meses_ou_crimes_ausentes')
        if pd.isna(local.populacao) or local.populacao <= 0:
            motivos.append('populacao_indisponivel')
        if score is None and not motivos:
            motivos.append('coorte_ou_critic_insuficiente')
        ano_pop = None if pd.isna(local.ano_populacao) else int(local.ano_populacao)
        if ano_pop is not None and ultimo.year-ano_pop > 2:
            motivos.append('populacao_defasada')
        if idade_meses > 3:
            motivos.append('serie_defasada')
        confianca = ('insuficiente' if score is None else 'revisar' if motivos or diagnostico['rejeicoes_importacao'] else 'completo_na_fonte')
        densidade = float(local.populacao/local.area_km2) if pd.notna(local.populacao) and pd.notna(local.area_km2) and local.area_km2 > 0 else None
        detalhes = {'motivos': motivos, 'meses_por_crime': {c: int(contagem_meses.loc[codigo, c]) for c in crimes},
                    'crimes': detalhes_crimes.get(codigo, {}), 'idade_serie_meses': idade_meses,
                    'aviso': 'Índice relativo, não probabilidade. Completude não mede subnotificação.'}
        resultado.append({'codigo_ibge': codigo, 'municipio': local.municipio, 'uf': local.uf,
                          'populacao': None if pd.isna(local.populacao) else float(local.populacao),
                          'ano_populacao': ano_pop, 'area_km2': None if pd.isna(local.area_km2) else float(local.area_km2),
                          'densidade_hab_km2': densidade, 'indice_roubo_0_100': score, 'faixa': faixa(score),
                          'confianca': confianca, 'completude_0_1': completude,
                          'inicio': meses[0][:7], 'fim': str(ultimo), 'detalhes': detalhes})
    df = pd.DataFrame(resultado)
    df['indice_roubo_0_100'] = pd.to_numeric(df.indice_roubo_0_100, errors='raise').astype(float)
    cobertura = []
    for uf, grupo in df.groupby('uf', sort=True):
        cobertura.append({'uf': uf, 'municipios_ibge': len(grupo),
                          'com_12_meses_todos_crimes': int(completos.loc[grupo.codigo_ibge].sum()),
                          'com_indice': int(grupo.indice_roubo_0_100.notna().sum()),
                          'completude_media_0_1': float(grupo.completude_0_1.mean())})
    diagnostico['cobertura_uf'] = cobertura
    diagnostico['topo_revisao'] = json.loads(df.dropna(subset=['indice_roubo_0_100']).nlargest(30, 'indice_roubo_0_100').to_json(orient='records', force_ascii=False))
    # A pontuação nacional refere-se apenas à coorte observada; UFs ausentes são visíveis.
    sem_cobertura = [c['uf'] for c in cobertura if c['com_indice'] == 0]
    if sem_cobertura:
        diagnostico['alertas'].append('UFs sem índice: '+', '.join(sem_cobertura))
    execucao = con.execute('INSERT INTO execucoes(criado_em,parametros,diagnostico) VALUES(?,?,?)',
                          (datetime.now(timezone.utc).isoformat(), json.dumps({'crimes': crimes, 'fim': str(ultimo)}),
                           json.dumps(diagnostico, ensure_ascii=False, allow_nan=False))).lastrowid
    con.execute('DELETE FROM indices')
    for r in resultado:
        con.execute('INSERT INTO indices VALUES(?,?,?,?,?,?,?,?,?)',
                    (r['codigo_ibge'], r['indice_roubo_0_100'], r['faixa'], r['confianca'], r['completude_0_1'],
                     r['inicio'], r['fim'], json.dumps(r['detalhes'], ensure_ascii=False), execucao))
    return df, diagnostico
