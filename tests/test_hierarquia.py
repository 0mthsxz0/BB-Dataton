"""Fixtures sintéticas: a seleção não pode transformar lacunas em certeza."""
import json

import pandas as pd
import pytest

from seguranca.banco import conectar, inicializar, registrar_fonte
from seguranca.hierarquia import (inicializar_hierarquia, resolver, salvar_candidatos,
                                  atualizar_hierarquia)
from seguranca.indice import gerar_indice


@pytest.fixture
def base(tmp_path):
    db = tmp_path/'teste.sqlite'
    arquivo = tmp_path/'fixture.txt'
    arquivo.write_text('fixture sintética')
    with conectar(db) as con:
        inicializar(con)
        inicializar_hierarquia(con)
        fid = registrar_fonte(con, arquivo, 'fixture:cadastro')
        con.execute('INSERT INTO municipios VALUES(?,?,?,?,?,?,?,?)',
                    ('3550308', 'São Paulo', 'SP', 1000, 10, 2025, 2022, fid))
    return db


def politica():
    return {'versao': 1, 'indicadores': {'Roubo de veículo': {'definicoes': ['aprovada', 'outra_aprovada']}},
            'fontes': [{'id': nome, 'nivel': nivel, 'ordem': 10, 'validada': True,
                        'metodologia_url': 'https://www.gov.br/metodologia', 'ufs': ['SP']}
                       for nome, nivel in [('primaria', 1), ('nacional', 2)]]}


def salvar(con, tmp_path, fornecedor, valor=10, nmeses=12, **extra):
    arquivo = tmp_path/(fornecedor+'.txt')
    arquivo.write_text('fixture '+fornecedor+str(valor), encoding='utf-8')
    fonte = registrar_fonte(con, arquivo, 'fixture:'+fornecedor)
    registros = [{'codigo_ibge': '3550308', 'crime': 'Roubo de veículo', 'mes': f'2025-{mes:02d}',
                  'valor': valor, 'metrica': 'ocorrencias', 'granularidade': 'municipio',
                  'definicao': 'aprovada', 'consolidado': True, **extra}
                 for mes in range(1, nmeses+1)]
    salvar_candidatos(con, fornecedor, fonte, registros)
    return fonte


def test_primaria_com_zero_prevalece_sem_somar_e_preserva_divergencias(base, tmp_path):
    with conectar(base) as con:
        ativos = {'primaria': salvar(con, tmp_path, 'primaria', 0),
                  'nacional': salvar(con, tmp_path, 'nacional', 40)}
        d, escolhas = resolver(con, politica(), ativos, '2025-12')
        assert escolhas[0]['fornecedor'] == 'primaria'
        assert con.execute('SELECT count(*),sum(ocorrencias) FROM ocorrencias').fetchone()[:] == (12, 0)
        assert len(d['divergencias'][0]['meses_divergentes']) == 12


def test_desce_para_segunda_fonte_sem_remendar_meses(base, tmp_path):
    with conectar(base) as con:
        ativos = {'primaria': salvar(con, tmp_path, 'primaria', 1, nmeses=11),
                  'nacional': salvar(con, tmp_path, 'nacional', 20)}
        d, escolhas = resolver(con, politica(), ativos, '2025-12')
        assert escolhas[0]['fornecedor'] == 'nacional'
        assert escolhas[0]['tentativas'][0]['motivo'] == 'serie_incompleta'
        assert con.execute('SELECT sum(ocorrencias) FROM ocorrencias').fetchone()[0] == 240
        assert d['observacoes_publicadas'] == 12


@pytest.mark.parametrize('extra', [dict(metrica='vitimas'), dict(granularidade='estado'),
                                  dict(definicao='nao_aprovada'), dict(consolidado=False)])
def test_incompatibilidade_independe_da_reputacao_da_fonte(base, tmp_path, extra):
    with conectar(base) as con:
        ativos = {'primaria': salvar(con, tmp_path, 'primaria', **extra),
                  'nacional': salvar(con, tmp_path, 'nacional')}
        _, escolhas = resolver(con, politica(), ativos, '2025-12')
        assert escolhas[0]['fornecedor'] == 'nacional'
        assert escolhas[0]['tentativas'][0]['motivo'] != 'selecionada'


def test_sem_fonte_compativel_mantem_lacuna_e_pesos_vazios(base, tmp_path):
    with conectar(base) as con:
        ativos = {'primaria': salvar(con, tmp_path, 'primaria', nmeses=11)}
        d, escolhas = resolver(con, politica(), ativos, '2025-12')
        assert d['series_sem_fonte'] == 1
        assert escolhas[0]['status'] == 'fontes_esgotadas'
        assert con.execute('SELECT count(*) FROM ocorrencias').fetchone()[0] == 0
        _, indice = gerar_indice(con, ['Roubo de veículo'], '2025-12')
        assert indice['pesos_critic'] == {}


def test_definicao_nao_pode_mudar_no_meio_da_serie(base, tmp_path):
    with conectar(base) as con:
        fonte = salvar(con, tmp_path, 'primaria')
        con.execute("UPDATE hierarquia_candidatos SET definicao='outra_aprovada' WHERE mes='2025-12-01'")
        _, escolhas = resolver(con, politica(), {'primaria': fonte}, '2025-12')
        assert escolhas[0]['status'] == 'fontes_esgotadas'
        assert escolhas[0]['tentativas'][0]['motivo'] == 'definicao_muda_na_serie'


def test_reexecucao_idempotente_e_revisao_da_fonte_gerida(base, tmp_path):
    with conectar(base) as con:
        fonte = salvar(con, tmp_path, 'primaria', 5)
        resolver(con, politica(), {'primaria': fonte}, '2025-12')
        resolver(con, politica(), {'primaria': fonte}, '2025-12')
        nova = salvar(con, tmp_path, 'primaria', 6)
        resolver(con, politica(), {'primaria': nova}, '2025-12')
        assert con.execute('SELECT count(*),sum(ocorrencias) FROM ocorrencias').fetchone()[:] == (12, 72)
        assert con.execute('SELECT DISTINCT fonte_id FROM ocorrencia_fontes').fetchall()[0][0] == nova


def test_conflito_com_fonte_legada_reverte_transacao(base, tmp_path):
    with conectar(base) as con:
        fonte = salvar(con, tmp_path, 'primaria', 20)
        legado = con.execute('SELECT min(id) FROM fontes').fetchone()[0]
        con.execute('INSERT INTO ocorrencias VALUES(?,?,?,?)', ('3550308','roubo de veiculos','2025-01-01',2))
        con.execute('INSERT INTO ocorrencia_fontes VALUES(?,?,?,?)', ('3550308','roubo de veiculos','2025-01-01',legado))
    with pytest.raises(RuntimeError, match='legada conflitante'):
        with conectar(base) as con:
            resolver(con, politica(), {'primaria': fonte}, '2025-12')
    with conectar(base) as con:
        assert con.execute('SELECT count(*),sum(ocorrencias) FROM ocorrencias').fetchone()[:] == (1, 2)


def test_falha_de_coleta_continua_para_proximo_adaptador(base, tmp_path, monkeypatch):
    from seguranca import hierarquia
    p = politica()
    for f in p['fontes']:
        f.update(adaptador='csv_normalizado', url='https://www.gov.br/'+f['id'], arquivo=f['id']+'.csv')
    arquivo = tmp_path/'nacional.csv'
    pd.DataFrame([{'codigo_ibge':'3550308', 'crime':'Roubo de veículo', 'mes':f'2025-{m:02d}',
                   'valor':4, 'metrica':'ocorrencias', 'granularidade':'municipio',
                   'definicao':'aprovada', 'consolidado':'SIM'} for m in range(1,13)]).to_csv(arquivo,index=False)
    def baixar(url, destino, atualizar):
        if url.endswith('primaria'):
            raise OSError('fixture: serviço fora do ar')
        return {'sha256': 'fixture'}
    monkeypatch.setattr(hierarquia, 'download', baixar)
    with conectar(base) as con:
        d = atualizar_hierarquia(con, p, tmp_path, '2025-12', tmp_path/'saida')
        assert d['series_selecionadas'] == 1 and 'primaria' in d['erros_fontes']
        assert con.execute('SELECT sum(ocorrencias) FROM ocorrencias').fetchone()[0] == 48


def test_definicoes_de_fontes_diferentes_nao_viram_ranking_nacional(base, tmp_path):
    with conectar(base) as con:
        fid = con.execute('SELECT min(id) FROM fontes').fetchone()[0]
        for codigo in ['3550309', '3550310']:
            con.execute('INSERT INTO municipios VALUES(?,?,?,?,?,?,?,?)', (codigo, codigo, 'SP', 2000, 20, 2025, 2022, fid))
        primeira = salvar(con, tmp_path, 'primaria', 5)
        segunda = salvar(con, tmp_path, 'nacional', 9, definicao='outra_aprovada')
        # O segundo fornecedor cobre cidades ausentes do primeiro, com outra definição.
        registros = []
        for codigo, valor in [('3550309', 10), ('3550310', 20)]:
            registros.extend([
                {'codigo_ibge':codigo,'crime':'Roubo de veículo','mes':f'2025-{m:02d}',
                 'valor':valor,'metrica':'ocorrencias','granularidade':'municipio',
                 'definicao':'outra_aprovada','consolidado':True} for m in range(1,13)])
        salvar_candidatos(con, 'nacional', segunda, registros)
        resolver(con, politica(), {'primaria':primeira,'nacional':segunda}, '2025-12')
        df, d = gerar_indice(con, ['Roubo de veículo'], '2025-12', minimo_municipios=3)
        assert d['municipios_elegiveis'] == 3
        assert df.indice_roubo_0_100.isna().all() and d['pesos_critic'] == {}
        assert any('equivalência' in a for a in d['alertas'])
