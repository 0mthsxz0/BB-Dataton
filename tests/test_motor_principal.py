"""Fixtures artificiais do contrato; nunca publicadas na base real."""
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from seguranca.banco import conectar, inicializar
from seguranca.motor_principal import importar_referencia, consultar_motor, exportar_motor
from seguranca.politica_motor import avaliar_seguranca, verificar_snapshot
from seguranca.vde import importar_vde, COLUNAS


@pytest.fixture
def banco(tmp_path):
    db = tmp_path/'fixture.sqlite'
    with conectar(db) as con:
        inicializar(con)
    return db


def escrever(tmp_path, **mudancas):
    total, denominador, referencia = 20, 1000, 10
    taxa = total/denominador*1000
    r = dict(codigo_ibge_municipio='3304557',municipio='Rio de Janeiro',uf='RJ',
        seguranca_da_cidade_0_1=referencia/(taxa+referencia),
        fonte_seguranca='https://www.ispdados.rj.gov.br/fixture.csv',periodo_seguranca='2025',
        granularidade_seguranca='MUNICIPIO',confianca_seguranca_0_1=.6,
        metodologia_seguranca='Fixture sintética apenas para teste do contrato',indicador_disponivel='SIM',
        categoria_seguranca='ROUBO_EM_COMERCIO',roubo_comercio_total=total,
        estabelecimentos_referencia=denominador,taxa_por_mil_estabelecimentos=taxa,
        referencia_taxa_por_mil=referencia,fonte_denominador='https://www.ibge.gov.br/fixture.csv',
        ano_denominador='2025',meses_observados_seguranca=12,cobertura_municipal_completa='SIM',
        sha256_arquivos='a'*64,atualizado_em_utc='2026-10-29T00:00:00+00:00',**{})
    r.update(mudancas)
    p=tmp_path/'fixture.csv'
    pd.DataFrame([r]).to_csv(p,index=False)
    p.with_name(p.name+'.manifesto.json').write_text(json.dumps({'arquivos':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()}}))
    return p


def test_roundtrip_valida_mesmo_contrato_da_main_e_relocalizacao(banco,tmp_path):
    p=escrever(tmp_path)
    with conectar(banco) as con:
        importar_referencia(con,p,'2026-10-29')
        importar_referencia(con,p,'2026-10-29')
        assert con.execute('SELECT count(*) FROM referencias_motor').fetchone()[0]==1
    with conectar(banco,somente_leitura=True) as con:
        r=exportar_motor(con,tmp_path/'pacote','2026-10-29')
    csv=Path(r['csv'])
    assert verificar_snapshot(csv)=='VERIFICADA'
    linhas=pd.read_csv(csv,dtype=str).to_dict('records')
    assert avaliar_seguranca(dict(linhas[0],integridade_seguranca='VERIFICADA'),'2026-10-29')['utilizavel']
    shutil.copytree(csv.parent,tmp_path/'outra-maquina')
    assert verificar_snapshot(tmp_path/'outra-maquina'/csv.name)=='VERIFICADA'
    with conectar(banco,somente_leitura=True) as con:
        assert consultar_motor(con,'3304557','2028-10-29')['municipios_utilizaveis']==0
        with pytest.raises(ValueError,match='Destino já existe'):
            exportar_motor(con,tmp_path/'pacote','2026-10-29')


@pytest.mark.parametrize('mudancas',[
    {'categoria_seguranca':'ROUBO_DE_VEICULOS'},
    {'ano_denominador':'2024'}, {'meses_observados_seguranca':11},
    {'granularidade_seguranca':'ESTADO'}, {'taxa_por_mil_estabelecimentos':1},
    {'tipo_seguranca':'SIMULACAO'}, {'confianca_seguranca_0_1':0},
    {'fonte_denominador':'https://example.com/fixture'},
])
def test_nao_converte_dados_incompativeis_em_referencia(banco,tmp_path,mudancas):
    p=escrever(tmp_path,**mudancas)
    with conectar(banco) as con,pytest.raises(ValueError):
        importar_referencia(con,p,'2026-10-29')


def test_hash_alterado_rejeitado(banco,tmp_path):
    p=escrever(tmp_path);p.write_bytes(p.read_bytes()+b'\n')
    with conectar(banco) as con,pytest.raises(ValueError,match='Integridade'):
        importar_referencia(con,p,'2026-10-29')


def test_base_vazia_nao_publica_csv_de_producao(banco,tmp_path):
    with conectar(banco,somente_leitura=True) as con:
        r=exportar_motor(con,tmp_path/'pendente','2026-10-29')
    assert r['status']=='PENDENTE_FONTES_COMPATIVEIS'
    assert (tmp_path/'pendente'/'diagnostico_motor.json').exists()
    assert not (tmp_path/'pendente'/'seguranca_ssp.csv').exists()


def test_csv_de_clientes_nao_aceito(banco,tmp_path):
    p=escrever(tmp_path,empresa_id='fixture')
    d=pd.read_csv(p)[['empresa_id']];d.to_csv(p,index=False)
    p.with_name(p.name+'.manifesto.json').write_text(json.dumps({'arquivos':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()}}))
    with conectar(banco) as con,pytest.raises(ValueError,match='cadastros de clientes'):
        importar_referencia(con,p,'2026-10-29')


def test_vde_bruto_antes_do_ibge_nao_publica_ocorrencia(banco,tmp_path):
    from openpyxl import Workbook
    p=tmp_path/'fixture.xlsx';w=Workbook();w.active.append(COLUNAS)
    row=dict.fromkeys(COLUNAS);row.update(uf='RJ',municipio='Rio de Janeiro',evento='Roubo de veículo',
        data_referencia='2025-01-01',total=5,abrangencia='Estadual')
    w.active.append([row[k] for k in COLUNAS]);w.save(p)
    with conectar(banco) as con:
        r=importar_vde(con,p,'fixture:vde',somente_bruto=True)
        assert r['status']=={'aguardando_validacao_municipal':1}
        assert con.execute('SELECT count(*) FROM ocorrencias').fetchone()[0]==0
        assert con.execute('SELECT count(*) FROM vde_registros').fetchone()[0]==1


def test_auditoria_de_cobertura_nao_grava_clientes(banco,tmp_path):
    from seguranca.auditoria import auditar
    p=tmp_path/'fixture_clientes.csv'
    pd.DataFrame([dict(empresa_id='EMP_FIXTURE',imovel_id='UNIDADE_FIXTURE',
        codigo_ibge_municipio='3304557',municipio_real='Rio de Janeiro',uf_real='RJ')]).to_csv(p,index=False)
    with conectar(banco,somente_leitura=True) as con:
        antes=con.execute('SELECT name FROM sqlite_master ORDER BY name').fetchall()
        r=auditar(con,p,tmp_path/'auditoria_consumidor')
        depois=con.execute('SELECT name FROM sqlite_master ORDER BY name').fetchall()
        assert antes==depois
        assert r['estabelecimentos']==1
        assert not con.execute("SELECT 1 FROM sqlite_master WHERE name='estabelecimentos'").fetchone()
