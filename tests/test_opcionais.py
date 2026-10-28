"""Contratos do mapa de opcionais: indícios não viram exposições confirmadas."""
import copy
import pytest
from produto import REGRAS, personalizar
from opcionais import avaliar_opcionais, comparar_alternativas
from motor_pontuacao import MotorPontuacao
from recomendador import recomendar_plano

def avaliar(r,code):
    return next(x for x in avaliar_opcionais(r,REGRAS) if x['code']==code)

def test_21_itens_e_quatro_modalidades_de_lucro():
    assert len(REGRAS['adjustable'])+len(REGRAS['optional'])==21
    assert len([x for x in REGRAS['optional'] if x['code'].startswith('LUCRO_')])==4
    assert all(x['fields'] and x['question'] for x in REGRAS['optional'])

def test_eletronicos_candidato_com_evidencia_sem_inclusao(registro):
    original=copy.deepcopy(registro)
    e=avaliar(registro,'EQUIPAMENTOS_ELETRONICOS')
    assert e['candidata'] and e['confirmacao'] is None
    assert e['estado']=='CONFIRMAR_EXPOSICAO'
    assert next(s['valor'] for s in e['evidencias'] if s['campo']=='informatica_ponderada')==10000
    assert registro==original

def test_eletrico_nao_prova_eletronico_e_venda_online_nao_prova_home_office():
    r={'equipamentos_ponderados':100000,'percentual_vendas_online_estimado':90}
    assert not avaliar(r,'EQUIPAMENTOS_ELETRONICOS')['candidata']
    e=avaliar(r,'HOME_OFFICE')
    assert e['candidata'] and not e['sugerida'] and e['confirmacao'] is None

@pytest.mark.parametrize('code',[x['code'] for x in REGRAS['optional']])
def test_ausencia_confirmada_prevalece_sobre_sinais(code,registro):
    op=next(x['operation'] for x in REGRAS['optional'] if x['code']==code)
    r=dict(registro,probabilidade_delivery_referencia=.99,probabilidade_refrigeracao_referencia=.99,operacao_confirmada={op:False})
    e=avaliar(r,code)
    assert not e['sugerida'] and not e['candidata'] and e['estado']=='AUSENCIA_CONFIRMADA'

def test_sistema_seguranca_nao_prova_sprinklers():
    e=avaliar({'tipos_bens_cadastrados':['SISTEMA_SEGURANCA']},'VAZAMENTO_SPRINKLERS')
    assert not e['candidata'] and e['confirmacao'] is None

def test_alternativas_preservam_lacunas_criticas(registro,catalogo):
    motor=MotorPontuacao()
    rec=recomendar_plano(motor.analisar_registro(registro),catalogo,registro=registro)
    a=comparar_alternativas(rec,avaliar_opcionais(registro,REGRAS))
    for x,c in zip(a,rec['comparacao']):
        assert x['adequado']==(c['apto_simulacao'] and not rec['indicacao_bloqueada'])
        assert x['lacunas']==c['indispensaveis_ausentes']
        assert x['preco'] is None
    assert 'EQUIPAMENTOS_ELETRONICOS' in a[0]['opcionais_para_avaliar']

def test_delivery_confirmado_impede_alternativa_essencial(registro,catalogo):
    r=dict(registro,operacao_confirmada={'delivery':True})
    rec=recomendar_plano(MotorPontuacao().analisar_registro(r),catalogo,registro=r)
    a=comparar_alternativas(rec,avaliar_opcionais(r,REGRAS))[0]
    assert not a['adequado'] and a['opcionais_incompativeis']==['Delivery']

def test_selecao_exige_confirmacao_e_modalidade_unica(registro,catalogo):
    motor=MotorPontuacao()
    rec=recomendar_plano(motor.analisar_registro(registro),catalogo,registro=registro)
    with pytest.raises(ValueError,match='confirmação'):
        personalizar(dict(registro,adicionais_escolhidos=['EQUIPAMENTOS_ELETRONICOS']),rec,{})
    with pytest.raises(ValueError,match='apenas uma modalidade'):
        personalizar(dict(registro,operacao_confirmada={'interruption':True},adicionais_escolhidos=['LUCRO_BRUTO_SIMPLES','LUCRO_LIQUIDO_AMPLA']),rec,{})
    p=personalizar(dict(registro,operacao_confirmada={'electronics':True},adicionais_escolhidos=['EQUIPAMENTOS_ELETRONICOS']),rec,{})
    assert p['pacote']['adicionais_condicionais']==['EQUIPAMENTOS_ELETRONICOS']
    assert set(REGRAS['mandatory'])<=set(p['pacote']['coberturas'])

def test_agregacao_distingue_eletronicos_de_eletricos(pasta_csv):
    import pandas as pd
    from processamento import carregar_base
    path=pasta_csv/'bens_cadastrados.csv'
    bens=pd.read_csv(path)
    bens=pd.concat([bens,pd.DataFrame([dict(bens.iloc[0],bem_id='BEM_2',tipo_bem='EQUIPAMENTO_ELETRONICO',valor_cadastrado=20000,valor_bem_ponderado_referencia=10000),dict(bens.iloc[0],bem_id='BEM_3',tipo_bem='EQUIPAMENTO_COZINHA',valor_cadastrado=40000,valor_bem_ponderado_referencia=20000)])],ignore_index=True)
    bens.to_csv(path,index=False)
    r=carregar_base(pasta_csv).registro('EMP_TESTE','IMO_TESTE')
    assert r['eletronicos_ponderados']==60000
    assert r['bens_ponderados']==80000
    e=avaliar(r,'EQUIPAMENTOS_ELETRONICOS')
    assert next(v['valor'] for v in e['evidencias'] if v['campo']=='eletronicos_ponderados')==60000
    assert 'letreiros_ponderados' not in [v['campo'] for v in e['evidencias']]
