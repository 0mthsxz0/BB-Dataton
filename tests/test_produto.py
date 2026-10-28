import copy
import json

import pytest

from exportacao import analisar_base
from motor_pontuacao import MotorPontuacao, COMUNS, CIBER, EMPREGADOR
from processamento import carregar_base
from produto import REGRAS, adaptar_catalogo, personalizar, triagem
from recomendador import recomendar_plano


def resultado(registro, catalogo):
    motor = MotorPontuacao()
    rec = recomendar_plano(motor.analisar_registro(registro), catalogo, registro=registro)
    return personalizar(registro, rec, motor.dimensionar_coberturas(registro))


def test_catalogo_legado_adaptado_sem_mutar_arquivo(catalogo):
    original = catalogo.loc[catalogo.cobertura_fixa.ne(CIBER)].copy()
    antes = original.copy(deep=True)
    efetivo = adaptar_catalogo(original)
    assert original.equals(antes)
    assert efetivo.groupby('plano').size().to_dict() == {'ESSENCIAL':6,'PRATICO':8,'TOTAL':10}
    assert adaptar_catalogo(efetivo).equals(efetivo)
    assert set(REGRAS['mandatory']) == set(COMUNS)


@pytest.mark.parametrize('valor,bloqueado', [(7500000,False),(7500000.01,True)])
def test_limite_apenas_objeto_basico(valor,bloqueado):
    r = {'bens_ponderados':valor,'estoque_medio_estimado':0,'valor_predio_reposicao_brl':0,
         'despesa_fixa_mensal_estimada':99999999,'folha_pagamento_mensal':99999999}
    assert triagem(r)['bloqueado'] is bloqueado


def test_desconhecido_nao_rejeita_nem_aceita_automaticamente(registro,catalogo):
    r = dict(registro,material_parede_externa_cadastrado=None)
    p = resultado(r,catalogo)
    assert not p['triagem']['bloqueado']
    rec = recomendar_plano(MotorPontuacao().analisar_registro(r),catalogo,registro=r)
    assert rec['elegibilidade']['elegivel']=='PENDENTE'


def test_obra_exporta_encaminhamento_sem_oferta(pasta_csv):
    base=carregar_base(pasta_csv)
    base.estabelecimentos.loc[base.estabelecimentos.imovel_id.eq('IMO_TESTE'),'situacao_imovel_cadastral']='EM_OBRA'
    r,c,a=analisar_base(base)
    bloqueado=r.loc[r.imovel_id.eq('IMO_TESTE')].iloc[0]
    assert bloqueado.elegivel=='NAO' and bloqueado.plano_recomendado==''
    assert not c.imovel_id.eq('IMO_TESTE').any()
    assert c.imovel_id.eq('IMO_FILIAL').any()
    assert a[0]['recomendacao']['indicacao_bloqueada']


def test_necessidade_critica_nao_diluida_por_comuns(registro,catalogo,config):
    motor=MotorPontuacao(config=config)
    pontos=motor.analisar_registro(registro)
    pontos[EMPREGADOR].update(prioridade=90,prioridade_min=90,prioridade_max=90)
    for c in COMUNS: config['coberturas'][c]['peso_plano']=10000
    rec=recomendar_plano(pontos,catalogo,config,registro)
    assert rec['comparacao'][0]['atinge_meta']
    assert rec['plano_recomendado']=='TOTAL'
    assert EMPREGADOR in rec['coberturas_criticas']


def test_refrigeracao_estimada_sugere_sem_inventar_confirmacao(registro,catalogo):
    r=dict(registro,probabilidade_refrigeracao_referencia=.9)
    p=resultado(r,catalogo)
    extra=next(x for x in p['adicionais'] if x.get('operation')=='refrigeration')
    assert extra['sugerida'] and extra['confirmacao'] is None and not extra['solicitada']
    assert not p['pacote']['adicionais_condicionais']
    r['operacao_confirmada']={'refrigeration':False}
    assert not next(x for x in resultado(r,catalogo)['adicionais'] if x.get('operation')=='refrigeration')['sugerida']


def test_prefere_continuidade_sem_mudar_indices_ou_outro_registro(registro,catalogo):
    antes=copy.deepcopy(registro)
    r=dict(registro,prioridade_cliente='continuidade')
    motor=MotorPontuacao()
    assert motor.analisar_registro(r)==motor.analisar_registro(registro)
    rec=recomendar_plano(motor.analisar_registro(r),catalogo,registro=r)
    assert rec['necessidades'][CIBER]['peso']==1.5
    assert registro==antes


def test_ciber_obrigatoria_sem_indenizacao_inventada(registro):
    d=MotorPontuacao().dimensionar_coberturas(registro)[CIBER]
    assert d['faixa_valor_min'] is None and d['faixa_valor_max'] is None
    assert 'limite de indenização' in d['justificativa']
    json.dumps(d,allow_nan=False)
