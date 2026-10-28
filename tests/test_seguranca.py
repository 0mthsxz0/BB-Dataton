"""Fixtures artificiais exclusivas dos testes; não entram na base de segurança."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
import requests

from seguranca.banco import (conectar, inicializar, importar_ibge, importar_sinesp,
                             identificar_colunas, registrar_fonte)
from seguranca.consulta import consultar
from seguranca.fontes import download, oficial
from seguranca.indice import gerar_indice, percentil, pesos_critic, suavizar


CRIMES = ['Roubo de veículo', 'Roubo de carga']


@pytest.fixture
def db(tmp_path):
    caminho = tmp_path/'teste.sqlite'
    with conectar(caminho) as con:
        inicializar(con)
        arquivo = tmp_path/'fonte_teste.txt'
        arquivo.write_text('fixture sintética, não fonte SINESP')
        fonte = registrar_fonte(con, arquivo, 'fixture:teste')
        for i, pop in enumerate([1000, 100_000, 200_000, 50_000, 12_000, 300_000]):
            codigo = str(3550000+i)
            con.execute('INSERT INTO municipios VALUES(?,?,?,?,?,?,?,?)',
                        (codigo, f'Cidade teste {i}', 'SP', pop, 100, 2022, 2022, fonte))
    return caminho


def preencher(con, excluir=None):
    for i in range(6):
        for j, crime in enumerate(['roubo de veiculos', 'roubo de carga']):
            n = ([1, 30, 5, 12, 2, 40] if j == 0 else [0, 2, 40, 1, 4, 6])[i]
            for mes in range(1, 13):
                chave = (str(3550000+i), crime, f'2024-{mes:02d}-01')
                if chave != excluir:
                    con.execute('INSERT INTO ocorrencias VALUES(?,?,?,?)', (*chave, n))


def csv_teste(tmp_path, linhas, nome='sinesp.csv'):
    p = tmp_path/nome
    pd.DataFrame(linhas).to_csv(p, sep=';', index=False)
    return p


def linha(**extra):
    return {'Código IBGE': '3550000', 'Município': 'Cidade teste 0', 'UF': 'SP',
            'Ano': '2024', 'Mês': 'janeiro', 'Natureza': 'Roubo de veículo', 'Ocorrências': '0', **extra}


def test_importacao_zero_nao_vira_ausente_e_cache_nao_duplica(db, tmp_path):
    arquivo = csv_teste(tmp_path, [linha(), linha(**{'Mês': 'fevereiro', 'Ocorrências': ''})])
    with conectar(db) as con:
        a = importar_sinesp(con, arquivo, 'fixture:sinesp')
        b = importar_sinesp(con, arquivo, 'fixture:sinesp')
        assert a == b
        assert a['observacoes'] == 1 and a['ausentes'] == 1
        assert con.execute('SELECT ocorrencias FROM ocorrencias').fetchone()[0] == 0
        assert con.execute('SELECT count(*) FROM ocorrencia_fontes').fetchone()[0] == 1


def test_importacao_por_nome_exige_uf_e_correspondencia_exata(db, tmp_path):
    row = linha()
    row.pop('Código IBGE')
    arquivo = csv_teste(tmp_path, [row, {**row, 'Município': 'Cidade inexistente'}])
    with conectar(db) as con:
        resultado = importar_sinesp(con, arquivo, 'fixture:teste')
        assert resultado['observacoes'] == 1 and resultado['rejeicoes'] == 1
        assert 'unívoca' in con.execute('SELECT motivo FROM rejeicoes').fetchone()[0]


def test_esquema_nao_substitui_ocorrencias_por_vitimas():
    with pytest.raises(ValueError, match='vítimas'):
        identificar_colunas(['Código IBGE', 'Ano', 'Mês', 'Natureza', 'Vítimas'])
    with pytest.raises(ValueError, match='ambíguas'):
        identificar_colunas(['Código IBGE', 'Ano', 'Mês', 'Natureza', 'Ocorrências', 'Total ocorrências'])


def test_conflito_reverte_arquivo_inteiro(db, tmp_path):
    original = csv_teste(tmp_path, [linha()], 'original.csv')
    with conectar(db) as con:
        importar_sinesp(con, original, 'fixture:original')
    conflitante = csv_teste(tmp_path, [linha(**{'Mês': 'fevereiro', 'Ocorrências': 1}),
                                     linha(**{'Ocorrências': 2})], 'conflito.csv')
    with pytest.raises(RuntimeError, match='conflitantes'):
        with conectar(db) as con:
            importar_sinesp(con, conflitante, 'fixture:conflito')
    with conectar(db) as con:
        assert con.execute('SELECT count(*) FROM ocorrencias').fetchone()[0] == 1
        assert con.execute('SELECT count(*) FROM fontes').fetchone()[0] == 2


def test_duplicata_dentro_do_arquivo_nao_e_somada(db, tmp_path):
    arquivo = csv_teste(tmp_path, [linha(), linha()])
    with pytest.raises(RuntimeError, match='repetida'):
        with conectar(db) as con:
            importar_sinesp(con, arquivo, 'fixture:teste')
    with conectar(db) as con:
        assert con.execute('SELECT count(*) FROM ocorrencias').fetchone()[0] == 0


def test_planilha_com_cabecalho_deslocado_e_meses_em_colunas(db, tmp_path):
    p = tmp_path/'mensal.xlsx'
    with pd.ExcelWriter(p) as writer:
        pd.DataFrame([['Documento sintético de teste']]).to_excel(writer, sheet_name='metodologia', header=False, index=False)
        pd.DataFrame([{'Código IBGE': '3550000', 'Ano': '2024', 'Natureza': 'Roubo de carga',
                       'Janeiro': 0, 'Fevereiro': 2}]).to_excel(writer, sheet_name='municipios', startrow=3, index=False)
    with conectar(db) as con:
        r = importar_sinesp(con, p, 'fixture:teste')
        assert r['observacoes'] == 2
        assert r['folhas'][0]['nome'] == 'municipios'


def test_codigo_nome_e_uf_divergentes_sao_rejeitados(db, tmp_path):
    arquivo = csv_teste(tmp_path, [linha(), linha(**{'Mês': 'fevereiro', 'UF': 'RJ'}),
                                 linha(**{'Mês': 'março', 'Ocorrências': -1}),
                                 linha(**{'Mês': 'abril', 'Município': 'Outro nome'})])
    with conectar(db) as con:
        r = importar_sinesp(con, arquivo, 'fixture:teste')
        assert r['observacoes'] == 1 and r['rejeicoes'] == 3
        todo_rejeitado = csv_teste(tmp_path, [linha(**{'Código IBGE': '9999999'})], 'rejeitado.csv')
        r = importar_sinesp(con, todo_rejeitado, 'fixture:rejeitado')
        assert r['observacoes'] == 0 and r['rejeicoes'] == 1
        assert con.execute('SELECT count(*) FROM rejeicoes').fetchone()[0] == 4


def test_empate_percentil_e_critic_sem_pesos_manuais():
    assert percentil([0, 0, 1]).tolist() == [25, 25, 100]
    assert percentil([0, 0, 0]).tolist() == [50, 50, 50]
    pesos = pesos_critic({'a': [0, 50, 100], 'b': [0, 100, 0], 'constante': [50, 50, 50]})
    assert sum(pesos.values()) == pytest.approx(1)
    assert pesos['constante'] == 0
    assert pesos['b'] > pesos['a']
    with pytest.raises(ValueError, match='redundantes'):
        pesos_critic({'a': [0, 50, 100], 'b': [0, 50, 100]})


def test_suavizacao_reduz_instabilidade_de_municipio_pequeno():
    contagens = np.array([3, 200, 10, 30])
    pop = np.array([100, 100000, 100000, 50000])
    taxas, peso, prior = suavizar(contagens, pop)
    assert prior['beta'] > 0
    assert peso[0] < peso[1]
    assert prior['media_nacional'] < taxas[0] < contagens[0]/pop[0]*100000
    taxa_zero, _, _ = suavizar([0, 0], [100, 10000])
    assert list(taxa_zero) == [0, 0]


def test_janela_comum_meses_ausentes_e_cobertura(db):
    with conectar(db) as con:
        preencher(con, excluir=('3550000', 'roubo de veiculos', '2024-12-01'))
        df, d = gerar_indice(con, CRIMES, '2024-12', minimo_municipios=3)
        assert len(df) == 6 and d['municipios_elegiveis'] == 5
        ausente = df.set_index('codigo_ibge').loc['3550000']
        assert pd.isna(ausente.indice_roubo_0_100)
        assert ausente.faixa == 'indisponivel'
        assert ausente.completude_0_1 == pytest.approx(23/24)
        assert d['cobertura_uf'][0]['com_12_meses_todos_crimes'] == 5
        assert df.fim.unique().tolist() == ['2024-12']
        assert any('não representa' in a for a in d['alertas'])


def test_area_e_contexto_nao_denominador_e_resultado_repetivel(db):
    with conectar(db) as con:
        preencher(con)
        a, d = gerar_indice(con, CRIMES, '2024-12', minimo_municipios=3)
        con.execute('UPDATE municipios SET area_km2=area_km2*100')
        b, _ = gerar_indice(con, CRIMES, '2024-12', minimo_municipios=3)
        assert a.indice_roubo_0_100.tolist() == b.indice_roubo_0_100.tolist()
        assert a.densidade_hab_km2.tolist() != b.densidade_hab_km2.tolist()
        assert a.indice_roubo_0_100.notna().all()
        assert a.indice_roubo_0_100.between(0, 100).all()
        assert sum(d['pesos_critic'].values()) == pytest.approx(1)
        for r in a.to_dict('records'):
            armazenado = con.execute('SELECT indice_roubo_0_100 FROM indices WHERE codigo_ibge=?', (r['codigo_ibge'],)).fetchone()[0]
            assert armazenado == r['indice_roubo_0_100']


def test_sem_coorte_sem_crime_e_sem_dispersao_nao_fabricam_indice(db):
    with conectar(db) as con:
        preencher(con)
        df, d = gerar_indice(con, CRIMES, '2024-12')
        assert df.indice_roubo_0_100.isna().all()
        assert 'insuficiente' in d['alertas'][0]
        with pytest.raises(ValueError, match='ausentes'):
            gerar_indice(con, ['Roubo de carga', 'Roubo a instituição financeira'], '2024-12')
        with pytest.raises(ValueError, match='só admite'):
            gerar_indice(con, ['Furto de veículo'], '2024-12')
        con.execute('UPDATE ocorrencias SET ocorrencias=0')
        df, d = gerar_indice(con, CRIMES, '2024-12', minimo_municipios=3)
        assert df.indice_roubo_0_100.isna().all()
        assert any('dispersão' in a for a in d['alertas'])


def test_consulta_readonly_e_municipio_sem_indice(db, tmp_path):
    r = consultar(db, uf='SP', busca='CIDADE TESTE 1')
    assert r['dados']['municipios'][0]['codigo_ibge'] == '3550001'
    r = consultar(db, codigo='3550001')
    assert r['status'] == 200 and r['dados']['indice_roubo_0_100'] is None
    assert consultar(db, codigo="' OR 1=1")['status'] == 400
    assert consultar(db, codigo='9999999')['status'] == 404
    with pytest.raises(sqlite3.OperationalError):
        consultar(tmp_path/'nao-existe.sqlite', codigo='3550001')
    assert not (tmp_path/'nao-existe.sqlite').exists()


def test_importar_ibge_mantem_ano_populacao_area_e_fonte(tmp_path):
    localidades = tmp_path/'municipios.json'
    indicadores = tmp_path/'indicadores.json'
    localidades.write_text(json.dumps([{'id': 3550308, 'nome': 'São Paulo',
        'regiao-imediata': {'regiao-intermediaria': {'UF': {'sigla': 'SP'}}}}]))
    indicadores.write_text(json.dumps([{'id': var, 'resultados': [{'series': [
        {'localidade': {'id': '3550308'}, 'serie': {'2022': valor}}]}]}
        for var, valor in [('93', '11451999'), ('6318', '1521.202')]]))
    with conectar(tmp_path/'ibge.sqlite') as con:
        inicializar(con)
        assert importar_ibge(con, localidades, indicadores, 'fixture:local', 'fixture:indicadores') == 1
        r = con.execute('SELECT * FROM municipios').fetchone()
        assert r['populacao'] == 11451999 and r['area_km2'] == 1521.202
        assert r['ano_populacao'] == 2022
        assert con.execute('SELECT count(*) FROM fontes').fetchone()[0] == 2


def test_download_exige_origem_oficial_tls_e_cache_integro(tmp_path, monkeypatch):
    assert oficial('https://www.gov.br/mj/dados.xlsx')
    assert not oficial('https://www.gov.br.evil.example/arquivo')
    assert not oficial('http://www.gov.br/arquivo')
    def erro_tls(*args, **kwargs):
        assert kwargs.get('verify', True) is True
        raise requests.exceptions.SSLError('fixture: cadeia inválida')
    monkeypatch.setattr(requests, 'get', erro_tls)
    with pytest.raises(requests.exceptions.SSLError):
        download('https://www.gov.br/mj/dados.xlsx', tmp_path/'dados.xlsx')
    assert not (tmp_path/'dados.xlsx').exists()


def test_cli_sem_base_retorna_503_sem_criar_arquivo(tmp_path):
    p = subprocess.run([sys.executable, '-m', 'seguranca', '--banco', str(tmp_path/'ausente.sqlite'),
                        'consultar', '--codigo', '3550308'], capture_output=True, text=True)
    assert p.returncode == 2 and json.loads(p.stdout)['status'] == 503
    assert not (tmp_path/'ausente.sqlite').exists()


def test_base_criada_sem_importacao_continua_indisponivel(tmp_path):
    db = tmp_path/'vazia.sqlite'
    with conectar(db) as con:
        inicializar(con)
    assert consultar(db, uf='SP', busca='São Paulo')['status'] == 503


def test_cli_gera_csv_manifesto_e_consulta_o_mesmo_indice(db, tmp_path):
    with conectar(db) as con:
        preencher(con)
    config = tmp_path/'config.json'
    config.write_text(json.dumps({'crimes_indice': CRIMES, 'minimo_municipios': 3}))
    destino = tmp_path/'exportacao'
    comando = [sys.executable, '-m', 'seguranca', '--banco', str(db)]
    gerar = subprocess.run(comando+['gerar-indice', '--config', str(config), '--fim', '2024-12',
                                   '--saida', str(destino)], capture_output=True, text=True)
    assert gerar.returncode == 0, gerar.stderr
    csv = pd.read_csv(destino/'indice_municipal.csv', dtype={'codigo_ibge': str})
    assert len(csv) == 6
    consulta = subprocess.run(comando+['consultar', '--codigo', '3550001'], capture_output=True, text=True)
    assert consulta.returncode == 0
    indice = json.loads(consulta.stdout)['dados']['indice_roubo_0_100']
    assert indice == pytest.approx(csv.set_index('codigo_ibge').loc['3550001'].indice_roubo_0_100)
    manifesto = json.loads((destino/'manifesto.json').read_text())
    assert len(manifesto['arquivos_sha256']['indice_municipal.csv']) == 64
    assert (destino/'cobertura_uf.csv').exists()
