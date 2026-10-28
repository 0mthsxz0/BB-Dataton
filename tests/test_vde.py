"""Testes das barreiras que a inspeção dos arquivos reais tornou necessárias."""
import json

import pandas as pd
import pytest

from seguranca.auditoria import auditar
from seguranca.banco import conectar, inicializar, importar_populacao, registrar_fonte
from seguranca.indice import gerar_indice
from seguranca.vde import COLUNAS, importar_vde


@pytest.fixture
def banco(tmp_path):
    caminho = tmp_path/'vde.sqlite'
    fonte = tmp_path/'fixture.txt'
    fonte.write_text('fixture artificial')
    with conectar(caminho) as con:
        inicializar(con)
        fid = registrar_fonte(con, fonte, 'fixture:teste')
        con.execute('INSERT INTO municipios VALUES(?,?,?,?,?,?,?,?)',
                    ('3550308', 'São Paulo', 'SP', 1000, 100, 2022, 2022, fid))
    return caminho


def linha(**kwargs):
    return {**dict.fromkeys(COLUNAS), 'uf': 'SP', 'municipio': 'SÃO PAULO',
            'evento': 'Roubo de veículo', 'data_referencia': pd.Timestamp('2025-01-01'),
            'total': 0, 'abrangencia': 'Estadual', **kwargs}


def planilha(tmp_path, linhas):
    # Fixture em arquivo é necessária para verificar o leitor do layout oficial.
    from openpyxl import Workbook
    arquivo = tmp_path/'fixture.xlsx'
    livro = Workbook()
    livro.active.append(COLUNAS)
    for r in linhas:
        livro.active.append([r[c] for c in COLUNAS])
    livro.save(arquivo)
    return arquivo


def test_vde_nao_rateia_estado_nem_mistura_unidades_e_abrangencias(banco, tmp_path):
    arquivo = planilha(tmp_path, [linha(), linha(municipio='NÃO INFORMADO', total=10),
        linha(evento='Roubo seguido de morte (latrocínio)', total=None, total_vitima=3),
        linha(abrangencia='Polícia Federal', total=4)])
    with conectar(banco) as con:
        a = importar_vde(con, arquivo, 'fixture:vde')
        b = importar_vde(con, arquivo, 'fixture:vde')
        assert a == b
        assert a['status'] == {'ocorrencia_municipal': 1, 'sem_municipio': 1,
                               'vitimas_nao_sao_ocorrencias': 1, 'abrangencia_nao_estadual': 1}
        assert con.execute('SELECT count(*) FROM vde_registros').fetchone()[0] == 4
        assert con.execute('SELECT count(*),sum(ocorrencias) FROM ocorrencias').fetchone()[:] == (1, 0)


def test_vde_chave_repetida_preservada_sem_soma(banco, tmp_path):
    arquivo = planilha(tmp_path, [linha(total=2), linha(total=3)])
    with conectar(banco) as con:
        a = importar_vde(con, arquivo, 'fixture:vde')
        assert a['status'] == {'chave_municipal_repetida': 2}
        assert con.execute('SELECT count(*) FROM ocorrencias').fetchone()[0] == 0
        assert a['chaves_estaduais_repetidas'] == 1


def test_sem_ocorrencias_exporta_lacunas_sem_criar_pesos_ou_ranking(banco, tmp_path):
    arquivo = tmp_path/'estabelecimentos.csv'
    pd.DataFrame([{'empresa_id': 'TESTE_1', 'imovel_id': 'UNIDADE_1',
                   'codigo_ibge_municipio': '3550308', 'municipio_real': 'Sao Paulo', 'uf_real': 'SP'},
                  {'empresa_id': 'TESTE_2', 'imovel_id': 'UNIDADE_2',
                   'codigo_ibge_municipio': '3550308', 'municipio_real': 'Sao Paulo', 'uf_real': 'RJ'}]).to_csv(arquivo, index=False)
    with conectar(banco) as con:
        with pytest.raises(ValueError, match='janela auditada'):
            gerar_indice(con, ['Roubo de veículo'])
        df, d = gerar_indice(con, ['Roubo de veículo'], '2025-12')
        assert df.indice_roubo_0_100.isna().all()
        assert d['pesos_critic'] == {} and d['topo_revisao'] == []
        assert df.completude_0_1.tolist() == [0]
        a = auditar(con, arquivo, tmp_path/'auditoria')
        assert a['correspondencia_ibge'] == 1 and a['com_indice'] == 0
        assert a['motivos_revisao'] == {'uf_divergente': 1}
        assert con.execute('SELECT count(*) FROM estabelecimentos').fetchone()[0] == 1
    lacunas = pd.read_csv(tmp_path/'auditoria/lacunas_municipio_crime.csv')
    assert lacunas.meses_presentes.tolist() == [0]
    assert len(lacunas.meses_ausentes.iloc[0].split('|')) == 12


def test_estimativa_atualiza_populacao_preservando_area_e_ano(banco, tmp_path):
    arquivo = tmp_path/'estimativa.json'
    dados = [{'id': '9324', 'unidade': 'Pessoas', 'resultados': [{'series': [
        {'localidade': {'id': '3550308'}, 'serie': {'2025': '1200'}}]}]}]
    arquivo.write_text(json.dumps(dados), encoding='utf-8')
    with conectar(banco) as con:
        importar_populacao(con, arquivo, 'fixture:estimativa', 2025)
        assert con.execute('SELECT populacao,ano_populacao,area_km2,ano_area FROM municipios').fetchone()[:] == (1200, 2025, 100, 2022)
        dados[0]['resultados'][0]['series'][0]['localidade']['id'] = '9999999'
        arquivo.write_text(json.dumps(dados), encoding='utf-8')
        with pytest.raises(ValueError, match='códigos diferentes'):
            importar_populacao(con, arquivo, 'fixture:incompativel', 2025)
