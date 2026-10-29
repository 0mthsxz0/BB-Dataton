"""Bases e notas artificiais isoladas para testar a conexão, não o risco real."""
import json
from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from contexto_seguranca import consultar_contexto,estado_base,IntegracaoSeguranca,assinatura_banco
from scripts.publicar_base_seguranca import publicar
from scripts.instalar_base_seguranca import instalar
from avaliacao_mosler import avaliar_mosler
from motor_pontuacao import MotorPontuacao,ROUBO,VENDAVAL,EMPREGADOR,VIDROS
from seguranca import avaliar_seguranca


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    monkeypatch.delenv('BB_SEGURANCA_DB',raising=False)
    monkeypatch.delenv('BB_SEGURANCA_MODO',raising=False)


def referencia():
    return dict(codigo_ibge_municipio='3550308',uf='SP',seguranca_da_cidade_0_1=.25,
        confianca_seguranca_0_1=.6,indicador_disponivel='SIM',periodo_seguranca='2025',
        fonte_seguranca='https://www.gov.br/fixture',metodologia_seguranca='Fixture de teste empresarial',
        fonte_denominador='https://www.ibge.gov.br/fixture',sha256_arquivos='a'*64,
        categoria_seguranca='ROUBO_EM_COMERCIO',ano_denominador='2025',meses_observados_seguranca=12,
        cobertura_municipal_completa='SIM',granularidade_seguranca='MUNICIPIO',roubo_comercio_total=30,
        estabelecimentos_referencia=1000,taxa_por_mil_estabelecimentos=30,referencia_taxa_por_mil=10)


@pytest.fixture
def origem(tmp_path):
    p=tmp_path/'origem.sqlite'
    with sqlite3.connect(p) as con:
        con.executescript('''
        CREATE TABLE fontes(id INTEGER PRIMARY KEY,url TEXT,sha256 TEXT,coletado_em TEXT);
        CREATE TABLE municipios(codigo_ibge TEXT PRIMARY KEY,municipio TEXT,uf TEXT,populacao REAL,area_km2 REAL,ano_populacao INTEGER,ano_area INTEGER,fonte_id INTEGER);
        CREATE TABLE ocorrencias(codigo_ibge TEXT,crime TEXT,mes TEXT,ocorrencias INTEGER,PRIMARY KEY(codigo_ibge,crime,mes));
        CREATE TABLE ocorrencia_fontes(codigo_ibge TEXT,crime TEXT,mes TEXT,fonte_id INTEGER);
        CREATE TABLE referencias_motor(codigo_ibge TEXT,ano INTEGER,dados TEXT);
        ''')
        con.execute('INSERT INTO fontes VALUES(1,?,?,?)',('https://www.gov.br/fixture','a'*64,'2026-01-01T00:00:00+00:00'))
        con.execute('INSERT INTO municipios VALUES(?,?,?,?,?,?,?,?)',('3550308','São Paulo','SP',1000,100,2025,2022,1))
        for mes in range(1,13):
            for crime in ['roubo em comercio','roubo de veiculos']:
                con.execute('INSERT INTO ocorrencias VALUES(?,?,?,?)',('3550308',crime,f'2025-{mes:02d}-01',0))
                con.execute('INSERT INTO ocorrencia_fontes VALUES(?,?,?,?)',('3550308',crime,f'2025-{mes:02d}-01',1))
        con.execute('INSERT INTO referencias_motor VALUES(?,?,?)',('3550308',2025,json.dumps(referencia())))
    return p


def release(tmp_path,origem,name='release'):
    pasta=tmp_path/name;publicar(origem,pasta,'2025-fixture')
    return pasta/'seguranca.sqlite'


def test_sem_configuracao_e_sem_arquivo_nao_criam_banco(tmp_path):
    assert consultar_contexto('3550308')['status']=='NAO_CONFIGURADO'
    p=tmp_path/'inexistente.sqlite'
    r=consultar_contexto('3550308',caminho=p)
    assert r['status']=='BASE_INDISPONIVEL' and not p.exists()


def test_publicar_instalar_consultar_preserva_zero_e_origem(origem,tmp_path):
    p=release(tmp_path,origem)
    destino=tmp_path/'instalacao';i=instalar(p.parent,destino)
    assert instalar(p.parent,destino)==i
    r=consultar_contexto('3550308','SP','2026-01-15',i['banco'])
    assert r['status']=='DISPONIVEL'
    assert r['indicadores'][0]['ocorrencias_12m']==0
    assert r['indicadores'][0]['taxa_por_100mil_habitantes']==0
    assert r['fontes'][0]['sha256']=='a'*64
    assert r['periodo']['inicio']=='2025-01'
    assert estado_base(i['banco'])['contagens']['municipios']==1
    assert consultar_contexto('3550308','RJ','2026-01-15',i['banco'])['status']=='LOCALIZACAO_INVALIDA'
    assert consultar_contexto('3304557','RJ','2026-01-15',i['banco'])['status']=='MUNICIPIO_NAO_ENCONTRADO'
    assert consultar_contexto('invalid','SP',caminho=i['banco'])['status']=='LOCALIZACAO_INVALIDA'


def test_serie_parcial_nao_anualiza_e_populacao_outro_ano_nao_e_denominador(origem,tmp_path):
    with sqlite3.connect(origem) as c:
        c.execute("DELETE FROM referencias_motor")
        c.execute("DELETE FROM ocorrencias WHERE crime='roubo em comercio' AND mes='2025-01-01'")
        c.execute('UPDATE municipios SET ano_populacao=2024')
    p=release(tmp_path,origem)
    r=consultar_contexto('3550308','SP','2026-01-15',p)
    assert r['status']=='PARCIAL'
    assert all(i['taxa_por_100mil_habitantes'] is None for i in r['indicadores'])
    comercio=next(i for i in r['indicadores'] if i['crime']=='roubo em comercio')
    assert comercio['meses_observados']==11 and comercio['ocorrencias_12m'] is None
    assert consultar_contexto('3550308','SP','2028-01-15',p)['indicadores'][0]['status']=='DESATUALIZADO'


@pytest.mark.parametrize('mudanca',['hash','versao','simulacao','cliente'])
def test_pacotes_incompativeis_nao_entram_no_motor(origem,tmp_path,mudanca):
    if mudanca=='cliente':
        with sqlite3.connect(origem) as c:c.execute('CREATE TABLE estabelecimentos(empresa_id TEXT)')
        with pytest.raises(ValueError,match='clientes'):release(tmp_path,origem)
        assert not (tmp_path/'release').exists();return
    if mudanca=='simulacao':
        with sqlite3.connect(origem) as c:
            c.execute('UPDATE referencias_motor SET dados=?',(json.dumps(dict(referencia(),tipo_seguranca='SIMULACAO')),))
    p=release(tmp_path,origem)
    mpath=Path(str(p)+'.manifesto.json')
    if mudanca in ('hash','versao'):
        m=json.loads(mpath.read_text());m['sha256' if mudanca=='hash' else 'versao_schema']='0'*64 if mudanca=='hash' else 999;mpath.write_text(json.dumps(m))
        r=consultar_contexto('3550308','SP','2026-01-15',p)
        assert r['status']=='BASE_INDISPONIVEL' and r['referencia_empresarial'] is None
    else:
        assert consultar_contexto('3550308','SP','2026-01-15',p)['referencia_empresarial'] is None


def test_modos_so_alteram_roubo_com_referencia_elegivel(origem,tmp_path,registro):
    p=release(tmp_path,origem)
    r=dict(registro,codigo_ibge_municipio='3550308',uf_real='SP')
    antes=dict(r)
    baseline=MotorPontuacao(data_analise='2026-01-15').analisar_registro(r)
    complementar=MotorPontuacao(data_analise='2026-01-15',banco_seguranca=p).analisar_registro(r)
    ativo=MotorPontuacao(data_analise='2026-01-15',banco_seguranca=p,modo_seguranca='referencia_validada').analisar_registro(r)
    assert r==antes
    assert complementar[ROUBO]['prioridade']==baseline[ROUBO]['prioridade']
    assert ativo[ROUBO]['prioridade']!=baseline[ROUBO]['prioridade']
    assert ativo[ROUBO]['qualidade_seguranca']['utilizavel']
    assert ativo[ROUBO]['contexto_seguranca']['aplicada_no_motor']
    assert ativo[ROUBO]['referencia_evento']['periodo_seguranca']=='2025'
    for c in [VENDAVAL,EMPREGADOR,VIDROS]:assert ativo[c]['prioridade']==baseline[c]['prioridade']
    velho=MotorPontuacao(data_analise='2028-10-29',banco_seguranca=p,modo_seguranca='referencia_validada').analisar_registro(r)
    assert not velho[ROUBO]['contexto_seguranca']['aplicada_no_motor']


def test_banco_corrompido_preserva_referencia_csv_e_nao_escreve_cliente(origem,tmp_path,registro):
    p=release(tmp_path,origem);antes=p.read_bytes()
    r=MotorPontuacao(banco_seguranca=p).analisar_registro(registro)
    assert p.read_bytes()==antes
    p.write_bytes(b'corrompido')
    r=MotorPontuacao(banco_seguranca=p,modo_seguranca='referencia_validada').analisar_registro(registro)
    assert r[ROUBO]['contexto_seguranca']['status']=='BASE_INDISPONIVEL'
    assert r[ROUBO]['qualidade_seguranca']['status']=='SIMULACAO' # fixture existente preservada


def test_mosler_exige_evidencias_e_nunca_multiplica_prioridade(origem,tmp_path,registro):
    a={'criterios':{k:{'nota':4,'evidencia':'Fixture técnica independente'} for k in 'FSPEAV'},'avaliador':'Teste','data_avaliacao':'2026-01-01'}
    s=avaliar_mosler(a,'2026-01-15')
    assert s['er']==512 and not s['aplicada_na_recomendacao']
    assert avaliar_mosler(None)['status']=='PENDENTE_AVALIACAO'
    a['criterios']['V']['nota']=True
    assert avaliar_mosler(a)['status']=='AVALIACAO_INVALIDA'
    motor=MotorPontuacao(data_analise='2026-01-15')
    sem=motor.analisar_registro(registro);com=motor.analisar_registro(dict(registro,avaliacao_mosler=a))
    assert com[ROUBO]['prioridade']==sem[ROUBO]['prioridade']


def test_cache_e_invalidacao_de_interface(origem,tmp_path,monkeypatch):
    p=release(tmp_path,origem);monkeypatch.setenv('BB_SEGURANCA_DB',str(p))
    sig=assinatura_banco();motor=IntegracaoSeguranca()
    r={'codigo_ibge_municipio':'3550308','uf_real':'SP'}
    assert motor.preparar(r,'2026-01-15')['contexto_seguranca']['status']=='DISPONIVEL'
    p.write_bytes(b'invalido')
    assert assinatura_banco()!=sig
    assert motor.preparar(r,'2026-01-15')['contexto_seguranca']['status']=='BASE_INDISPONIVEL'


def test_indicadores_sem_referencia_nao_substituem_evento(origem,tmp_path,registro):
    with sqlite3.connect(origem) as c:c.execute('DELETE FROM referencias_motor')
    p=release(tmp_path,origem)
    r=dict(registro,codigo_ibge_municipio='3550308',uf_real='SP')
    esperado=MotorPontuacao(data_analise='2026-01-15').analisar_registro(r)
    novo=MotorPontuacao(data_analise='2026-01-15',banco_seguranca=p,modo_seguranca='referencia_validada').analisar_registro(r)
    assert novo[ROUBO]['contexto_seguranca']['indicadores']
    assert novo[ROUBO]['prioridade']==esperado[ROUBO]['prioridade']
    assert not novo[ROUBO]['contexto_seguranca']['aplicada_no_motor']


def test_lote_e_servico_preservam_proveniencia_sqlite(origem,tmp_path,registro,catalogo,pasta_csv,monkeypatch):
    from exportacao import exportar
    from processamento import carregar_base
    from cotacao_service import montar_resultado
    p=release(tmp_path,origem);monkeypatch.setenv('BB_SEGURANCA_DB',str(p));monkeypatch.setenv('BB_SEGURANCA_MODO','referencia_validada')
    b=carregar_base(pasta_csv)
    b.estabelecimentos['codigo_ibge_municipio']='3550308';b.estabelecimentos['uf_real']='SP'
    exportar(b,destino=tmp_path/'saida',data_analise='2026-01-15')
    aud=json.loads((tmp_path/'saida/auditoria.json').read_text())
    assert all(a['contexto_seguranca']['aplicada_no_motor'] for a in aud)
    manifesto=json.loads((tmp_path/'saida/manifesto.json').read_text())
    assert manifesto['integracao_seguranca']['releases']
    r=dict(registro,codigo_ibge_municipio='3550308',uf_real='SP')
    resultado=montar_resultado(r,MotorPontuacao(data_analise='2026-01-15'),catalogo,{'id':'fixture'},None,None,[],{},False)
    assert resultado['contextoSeguranca']['aplicada_no_motor']
    assert resultado['indices'][ROUBO]['referencia_publica']['arquivo']=='seguranca.sqlite'
    assert 'SQLite' in resultado['indices'][ROUBO]['referencia_publica']['modo_acesso']


def test_manifesto_malformado_e_serie_invalida_falham_sem_expor_caminhos(origem,tmp_path):
    p=release(tmp_path,origem);m=Path(str(p)+'.manifesto.json');d=json.loads(m.read_text());d['gerado_em']=None;m.write_text(json.dumps(d))
    r=consultar_contexto('3550308','SP','2026-01-15',p)
    assert r['status']=='BASE_INDISPONIVEL' and str(tmp_path) not in json.dumps(r)
    with sqlite3.connect(origem) as c:c.execute("UPDATE ocorrencias SET ocorrencias=-1 WHERE mes='2025-01-01'")
    p=release(tmp_path,origem,'invalido')
    assert consultar_contexto('3550308','SP','2026-01-15',p)['status']=='BASE_INDISPONIVEL'


def test_fontes_divergentes_na_janela_impedem_total_anual_confiavel(origem,tmp_path):
    with sqlite3.connect(origem) as c:
        c.execute('DELETE FROM referencias_motor')
        c.execute('INSERT INTO fontes VALUES(2,?,?,?)',('https://www.gov.br/outra-fixture','b'*64,'2026-01-01T00:00:00+00:00'))
        c.execute("UPDATE ocorrencia_fontes SET fonte_id=2 WHERE mes='2025-01-01'")
    p=release(tmp_path,origem)
    r=consultar_contexto('3550308','SP','2026-01-15',p)
    assert all(i['ocorrencias_12m'] is None for i in r['indicadores'])
    assert all(i['status']=='PARCIAL' for i in r['indicadores'])
