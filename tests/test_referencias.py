import copy
import json
from pathlib import Path
import pandas as pd
import pytest
from referencias import classe_cnae,extrair_classes_nr4,indicador_climatico
from motor_pontuacao import MotorPontuacao,VENDAVAL,ROUBO
from processamento import carregar_base


def test_classe_cnae_e_descricao_multilinha_nr4():
    assert classe_cnae('4753-9/00')=='47539'
    assert classe_cnae('47.53-9')=='47539'
    assert classe_cnae('123') is None
    texto='47.53-9 Comércio de eletrodomésticos e equipamentos de áudio e\nvídeo 1\n47.54-7 Comércio de móveis 1\n'
    classes=extrair_classes_nr4(texto)
    assert [(x['classe_cnae'],x['grau_risco_nr4']) for x in classes]==[('47539',1),('47547',1)]


def test_clima_frequencias_e_ausencias_nao_viram_dias_seguros(config):
    serie={'time':['2025-01-01','2025-01-02','2025-01-04'],
           'wind_gusts_10m_max':[55,75,None],'precipitation_sum':[0,60,70]}
    r=indicador_climatico(serie,config['clima'])
    assert r['frequencia_rajada_forte']==1
    assert r['frequencia_rajada_severa']==.5
    assert r['frequencia_vento_chuva']==.5
    assert r['dias_esperados']==4 and r['dias_conjuntos_validos']==2
    assert r['completude']==.5


def test_clima_serie_inconsistente_rejeitada(config):
    with pytest.raises(ValueError):
        indicador_climatico({'time':['2025-01-01'],'wind_gusts_10m_max':[]},config['clima'])


def test_snapshot_publico_tem_metadados_e_cobertura():
    pasta=Path(__file__).resolve().parents[1]/'references'
    clima=pd.read_csv(pasta/'clima_municipal.csv')
    nr4=pd.read_csv(pasta/'nr4_cnae.csv',dtype=str)
    seguranca=pd.read_csv(pasta/'seguranca_municipal.csv')
    assert len(clima)==10 and len(seguranca)==27
    assert clima.completude.eq(1).all() and clima.dias_esperados.eq(10958).all()
    assert nr4.classe_cnae.is_unique and len(nr4)>650
    assert nr4.loc[nr4.classe_cnae.eq('45200'),'grau_risco_nr4'].iloc[0]=='3'
    assert nr4.loc[nr4.classe_cnae.eq('47539'),'grau_risco_nr4'].iloc[0]=='1'
    assert seguranca.seguranca_da_cidade_0_1.between(0,1).all()


def test_clima_config_divergente_nao_e_usada_silenciosamente(registro,config):
    r=dict(registro,exposicao_climatica_0_1=.8,confianca_clima_0_1=.5,
           metodologia_clima=json.dumps(config['clima']))
    antes=MotorPontuacao(config=config).analisar_registro(r)[VENDAVAL]
    alterado=copy.deepcopy(config);alterado['clima']['rajada_forte_kmh']=45
    depois=MotorPontuacao(config=alterado).analisar_registro(r)[VENDAVAL]
    assert antes['risco_evento_observado']
    assert not depois['risco_evento_observado']
    assert 'regenerar' in depois['fatores_evento'][0]['observacao']


def test_fontes_clima_e_seguranca_independentes(registro):
    r=dict(registro,exposicao_climatica_0_1=.8,confianca_clima_0_1=.55,
           confianca_seguranca_0_1=.2,fonte_clima='FONTE_CLIMA',fonte_seguranca='FONTE_SEGURANCA')
    s=MotorPontuacao().analisar_registro(r)
    assert s[VENDAVAL]['confianca_evento']==.55
    assert s[ROUBO]['confianca_evento']==.2
    assert 'FONTE_CLIMA' in s[VENDAVAL]['fatores_evento'][0]['observacao']
    assert 'FONTE_SEGURANCA' in s[ROUBO]['fatores_evento'][0]['observacao']


def test_confirmacoes_vidros_validacao_e_aplicacao(pasta_csv,tmp_path):
    p=tmp_path/'confirmacoes.csv'
    pd.DataFrame([{'empresa_id':'EMP_TESTE','imovel_id':'IMO_TESTE',
                  'possui_vidros_confirmado':'SIM','valor_vidros_reposicao_brl':25000}]).to_csv(p,index=False)
    base=carregar_base(pasta_csv,confirmacoes=p)
    r=base.registro('EMP_TESTE','IMO_TESTE')
    assert float(r['valor_vidros_reposicao_brl'])==25000
    c=pd.read_csv(p);c['possui_vidros_confirmado']='NAO';c.to_csv(p,index=False)
    with pytest.raises(ValueError,match='contraditória'):
        carregar_base(pasta_csv,confirmacoes=p)
