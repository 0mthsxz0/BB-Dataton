"""Cruzamento de três fontes com dados sintéticos, exclusivos dos testes."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from seguranca.banco import conectar, inicializar, registrar_fonte
from seguranca.mosler import (avaliar_cruzamento, avaliar_linha, calcular_mosler,
                              classificar_mosler, ler_estabelecimentos, validar_config)


@pytest.fixture
def cfg_mosler():
    path = Path(__file__).resolve().parents[1]/'config/seguranca_mosler.json'
    cfg = json.loads(path.read_text())
    cfg['minimo_municipios_contexto'] = 3
    return cfg


@pytest.fixture
def banco_mosler(tmp_path, cfg_mosler):
    db = tmp_path/'fontes.sqlite'
    with conectar(db) as con:
        inicializar(con)
        p = tmp_path/'fonte.txt'; p.write_text('fixture, não são dados oficiais')
        fonte = registrar_fonte(con, p, 'fixture:mosler', {'origem_dados': 'SINESP', 'sintetico': True})
        counts = [[10, 3, 80, 2, 40, 15], [7, 90, 2, 40, 10, 20],
                  [10, 40, 5, 2, 80, 30], [60, 3, 12, 70, 4, 10]]
        for i in range(6):
            codigo = str(3550000+i)
            con.execute('INSERT INTO municipios VALUES(?,?,?,?,?,?,?,?)',
                        (codigo, f'Cidade teste {i}', 'SP', 100000, 100, 2022, 2022, fonte))
            for j, crime in enumerate(cfg_mosler['pesos_crimes']):
                for mes in range(1, 13):
                    con.execute('INSERT INTO ocorrencias VALUES(?,?,?,?)',
                                (codigo, crime, f'2024-{mes:02d}-01', counts[j][i]))
                    con.execute('INSERT INTO ocorrencia_fontes VALUES(?,?,?,?)',
                                (codigo, crime, f'2024-{mes:02d}-01', fonte))
    return db


def unidade(**extra):
    return {'empresa_id': 'TESTE', 'imovel_id': 'TESTE_A', 'codigo_ibge_municipio': '3550000',
        'mosler_f': 4, 'mosler_s': 4, 'mosler_p': 3, 'mosler_e': 2, 'mosler_v': 3,
        'exposicao_atividade_1a5': 4, 'avaliador_mosler': 'Avaliador sintético',
        'data_avaliacao_mosler': '2026-10-28', 'evidencias_mosler': 'Fixture exclusiva do teste', **extra}


def escrever(tmp_path, linhas):
    p = tmp_path/'estabelecimentos.csv'
    pd.DataFrame(linhas).to_csv(p, index=False)
    return p


def cruzar(db, csv, cfg, **kwargs):
    with conectar(db, somente_leitura=True) as con:
        return avaliar_cruzamento(con, csv, cfg, '2024-12', '2026-10-28', **kwargs)


def test_formula_mosler_limites_e_faixas():
    minimo = calcular_mosler(1, 1, 1, 1, 1, 1)
    maximo = calcular_mosler(5, 5, 5, 5, 5, 5)
    assert minimo['er_mosler'] == 2 and minimo['indice_mosler_0_100'] == 0
    assert maximo['er_mosler'] == 1250 and maximo['indice_mosler_0_100'] == 100
    caso = calcular_mosler(4, 4, 3, 2, 4, 3)
    assert caso['er_mosler'] == (4*4+3*2)*4*3 == 264
    assert caso['indice_mosler_0_100'] == pytest.approx(20.9935897436)
    assert classificar_mosler(250) == ('muito baixo', 'baixo')
    assert classificar_mosler(251) == ('baixo', 'baixo')
    assert classificar_mosler(750) == ('normal', 'moderado')
    assert classificar_mosler(1001) == ('muito alto', 'muito alto')


@pytest.mark.parametrize('valor', [True, 0, 6, 2.5, float('inf'), 'nao sei'])
def test_notas_invalidas_nao_sao_aceitas(valor):
    with pytest.raises(ValueError):
        calcular_mosler(valor, 2, 2, 2, 2, 2)


def test_cruzamento_tres_fontes_preserva_unidade_e_audita(banco_mosler, cfg_mosler, tmp_path):
    csv = escrever(tmp_path, [unidade()])
    df, d = cruzar(banco_mosler, csv, cfg_mosler)
    assert len(df) == d['calculados'] == 1
    r = df.iloc[0]
    assert r.populacao_ibge == 100000 and r.area_km2_ibge == 100
    assert r.densidade_hab_km2 == 1000
    assert r.completude_sinesp_0_1 == 1 and 0 <= r.contexto_roubo_0_100 <= 100
    assert r.status == 'EXPERIMENTAL_NAO_CALIBRADO'
    assert r.auditoria['mosler']['F'] == 4
    ps = r.auditoria['contexto']['percentis']
    assert r.contexto_roubo_0_100 == pytest.approx(sum(cfg_mosler['pesos_crimes'][c]*ps[c] for c in ps))
    assert len(r.auditoria['sensibilidade_pesos']) == 12
    assert r.menor_indice_cenarios_pesos <= r.indice_mosler_0_100 <= r.maior_indice_cenarios_pesos
    assert len(d['csv_sha256']) == 64


def test_estabelecimentos_mesma_cidade_tem_riscos_diferentes_sem_repesar_contexto(banco_mosler, cfg_mosler, tmp_path):
    csv = escrever(tmp_path, [unidade(), unidade(imovel_id='TESTE_B', mosler_f=5, mosler_s=5, mosler_v=5)])
    a, _ = cruzar(banco_mosler, csv, cfg_mosler)
    assert a.contexto_roubo_0_100.nunique() == 1
    assert a.er_mosler.nunique() == 2
    csv = escrever(tmp_path, [unidade()])
    b, _ = cruzar(banco_mosler, csv, cfg_mosler)
    assert a.contexto_roubo_0_100.iloc[0] == b.contexto_roubo_0_100.iloc[0]


def test_sem_nota_ou_evidencia_csv_nao_gera_indice(banco_mosler, cfg_mosler, tmp_path):
    csv = escrever(tmp_path, [unidade(mosler_v='', evidencias_mosler='')])
    df, d = cruzar(banco_mosler, csv, cfg_mosler)
    assert d['pendentes'] == 1 and d['calculados'] == 0
    assert df.er_mosler.isna().all() and df.faixa_projeto.iloc[0] == 'indisponivel'
    assert 'ausente:mosler_v' in df.auditoria.iloc[0]['mosler']['motivos']


def test_mes_ausente_nao_vira_zero_nem_renormaliza_pesos(banco_mosler, cfg_mosler, tmp_path):
    with conectar(banco_mosler) as con:
        con.execute("DELETE FROM ocorrencia_fontes WHERE codigo_ibge='3550000' AND crime='roubo de carga' AND mes='2024-02-01'")
        con.execute("DELETE FROM ocorrencias WHERE codigo_ibge='3550000' AND crime='roubo de carga' AND mes='2024-02-01'")
    df, _ = cruzar(banco_mosler, escrever(tmp_path, [unidade()]), cfg_mosler)
    assert df.er_mosler.isna().all()
    assert df.completude_sinesp_0_1.iloc[0] == pytest.approx(47/48)
    assert 'contexto_ibge_sinesp_indisponivel' in df.auditoria.iloc[0]['mosler']['motivos']


def test_municipio_desconhecido_permanece_com_pendencia(banco_mosler, cfg_mosler, tmp_path):
    df, _ = cruzar(banco_mosler, escrever(tmp_path, [unidade(codigo_ibge_municipio='9999999')]), cfg_mosler)
    assert len(df) == 1 and df.er_mosler.isna().all()
    assert 'municipio_sem_correspondencia_ibge' in df.auditoria.iloc[0]['mosler']['motivos']


def test_somente_registro_ibge_sem_sinesp_e_pendente(banco_mosler, cfg_mosler, tmp_path):
    with conectar(banco_mosler) as con:
        con.execute('DELETE FROM ocorrencia_fontes')
        con.execute('DELETE FROM ocorrencias')
    df, d = cruzar(banco_mosler, escrever(tmp_path, [unidade()]), cfg_mosler)
    assert d['calculados'] == 0 and df.contexto_roubo_0_100.isna().all()


def test_banco_sem_ibge_e_pendente_em_vez_de_preencher_media(tmp_path, cfg_mosler):
    db = tmp_path/'vazio.sqlite'
    with conectar(db) as con:
        inicializar(con)
    df, d = cruzar(db, escrever(tmp_path, [unidade()]), cfg_mosler)
    assert d['calculados'] == 0 and len(df) == 1


def test_populacao_ibge_altera_contexto_area_nao_adiciona_risco(banco_mosler, cfg_mosler, tmp_path):
    csv = escrever(tmp_path, [unidade()])
    a, _ = cruzar(banco_mosler, csv, cfg_mosler)
    with conectar(banco_mosler) as con:
        con.execute('UPDATE municipios SET area_km2=area_km2*10')
    b, _ = cruzar(banco_mosler, csv, cfg_mosler)
    assert a.contexto_roubo_0_100.iloc[0] == b.contexto_roubo_0_100.iloc[0]
    assert a.er_mosler.iloc[0] == b.er_mosler.iloc[0]
    assert a.densidade_hab_km2.iloc[0] != b.densidade_hab_km2.iloc[0]
    with conectar(banco_mosler) as con:
        con.execute("UPDATE municipios SET populacao=10000000 WHERE codigo_ibge='3550000'")
    c, _ = cruzar(banco_mosler, csv, cfg_mosler)
    assert a.contexto_roubo_0_100.iloc[0] != c.contexto_roubo_0_100.iloc[0]


def test_nao_aceita_duplicatas_ou_colunas_que_substituem_fonte(banco_mosler, cfg_mosler, tmp_path):
    with pytest.raises(ValueError, match='duplicado'):
        ler_estabelecimentos(escrever(tmp_path, [unidade(), unidade()]))
    with pytest.raises(ValueError, match='reservadas'):
        cruzar(banco_mosler, escrever(tmp_path, [unidade(contexto_roubo_0_100=100)]), cfg_mosler)


def test_pesos_explicitos_e_avaliacao_futura_rejeitada(cfg_mosler):
    ruim = copy.deepcopy(cfg_mosler)
    ruim['pesos_crimes']['roubo de carga'] = .9
    with pytest.raises(ValueError, match='somar'):
        validar_config(ruim)
    linha = {**unidade(data_avaliacao_mosler='2027-01-01'), 'contexto_roubo_0_100': 70,
             'municipio_ibge': 'Teste', 'uf_ibge': 'SP'}
    r = avaliar_linha(linha, cfg_mosler, __import__('datetime').date(2026, 10, 28), '2024-12')
    assert r['status'] == 'PENDENTE_DADOS' and 'avaliacao_futura' in r['motivos']


def test_cli_exporta_todas_as_unidades_com_auditoria_e_pendencias(banco_mosler, cfg_mosler, tmp_path):
    csv = escrever(tmp_path, [unidade(), unidade(imovel_id='TESTE_B', mosler_f='')])
    config = tmp_path/'config.json'; config.write_text(json.dumps(cfg_mosler))
    destino = tmp_path/'saida'
    p = subprocess.run([sys.executable, '-m', 'seguranca', '--banco', str(banco_mosler),
        'avaliar-mosler', '--estabelecimentos', str(csv), '--config', str(config),
        '--fim', '2024-12', '--data-analise', '2026-10-28', '--saida', str(destino)], capture_output=True, text=True)
    assert p.returncode == 2, p.stderr
    assert json.loads(p.stdout)['calculados'] == 1
    out = pd.read_csv(destino/'indice_estabelecimentos_mosler.csv')
    assert len(out) == 2 and out.er_mosler.notna().sum() == 1
    audit = json.loads((destino/'auditoria_mosler.json').read_text())
    assert audit['diagnostico']['estabelecimentos'] == 2
    manifesto = json.loads((destino/'manifesto_mosler.json').read_text())
    assert len(manifesto['arquivos_sha256']['indice_estabelecimentos_mosler.csv']) == 64
    assert (destino/'cobertura_mosler.csv').exists()


def test_ssp_no_mesmo_banco_nao_substitui_sinesp(banco_mosler, cfg_mosler, tmp_path):
    with conectar(banco_mosler) as con:
        con.execute('UPDATE fontes SET url=?,metadados=?', ('https://ssp.exemplo.gov.br/arquivo', json.dumps({'fornecedor': 'SSP'})))
    df, d = cruzar(banco_mosler, escrever(tmp_path, [unidade()]), cfg_mosler)
    assert d['calculados'] == 0 and df.er_mosler.isna().all()
    assert d['fontes_sinesp_utilizadas'] == []
    assert any('não são usadas' in a for a in d['alertas'])
