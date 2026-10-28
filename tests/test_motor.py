import copy
import math
import pytest
from motor_pontuacao import (MotorPontuacao, ROUBO, ELETRICO, INCENDIO, VIDROS,
    CIBER, DESPESAS, ALUGUEL, TERCEIROS, EMPREGADOR, VENDAVAL, DECISORIAS, carregar_config, normalizar_financeiro)


def test_patrimonio_muda_impacto_sem_mudar_evento(registro):
    motor = MotorPontuacao()
    registro.update(estoque_medio_estimado=0,estoque_pico_estimado=0)
    pequeno = motor.analisar_registro(registro)[ROUBO]
    grande = motor.analisar_registro(dict(registro,bens_ponderados=3000000,bens_total_referencia=3000000))[ROUBO]
    assert grande['prioridade'] > pequeno['prioridade']
    assert grande['impacto_normalizado'] > pequeno['impacto_normalizado']
    assert grande['risco_evento_relativo'] == pequeno['risco_evento_relativo']
    assert grande['probabilidade_sinistro'] is None


def test_cidade_segura_nao_zera_protecao(registro):
    motor = MotorPontuacao()
    alto = dict(registro,bens_ponderados=3000000,bens_total_referencia=3000000)
    seguro = motor.analisar_registro(dict(alto,seguranca_da_cidade_0_1=1))[ROUBO]
    exposto = motor.analisar_registro(dict(alto,seguranca_da_cidade_0_1=0))[ROUBO]
    assert 0 < seguro['prioridade'] < exposto['prioridade']


def test_aumentar_equipamentos_afeta_dimensionamento_eletrico(registro):
    motor = MotorPontuacao()
    a = motor.dimensionar_coberturas(registro)[ELETRICO]
    b = motor.dimensionar_coberturas(dict(registro,equipamentos_ponderados=300000))[ELETRICO]
    assert b['faixa_valor_min'] > a['faixa_valor_min']
    assert 'prioridade' not in a


def test_digital_nao_e_quinto_indice_de_decisao(registro):
    motor = MotorPontuacao()
    a = motor.analisar_registro(dict(registro,dependencia_digital_pct=10))
    b = motor.analisar_registro(dict(registro,dependencia_digital_pct=95))
    assert a == b and CIBER not in a


def test_maturidade_nao_e_vulnerabilidade_cibernetica(registro):
    motor = MotorPontuacao()
    assert motor.analisar_registro(dict(registro,indice_maturidade_digital=0)) == motor.analisar_registro(dict(registro,indice_maturidade_digital=100))


def test_sinal_loja_afeta_vidros_sem_inventar_valor(registro):
    motor = MotorPontuacao()
    a = motor.analisar_registro(registro)[VIDROS]
    b = motor.analisar_registro(dict(registro,possui_termo_loja='SIM'))[VIDROS]
    assert b['prioridade'] > a['prioridade']
    assert b['faixa_valor_max'] is None


def test_area_sozinha_nao_prova_vidracas(registro):
    motor = MotorPontuacao()
    assert motor.analisar_registro(dict(registro,area_cadastrada_m2=10))[VIDROS]['prioridade'] == motor.analisar_registro(dict(registro,area_cadastrada_m2=100000))[VIDROS]['prioridade']


def test_atividade_nao_e_contada_novamente_como_impacto_financeiro_rc(registro):
    motor = MotorPontuacao()
    a = motor.dimensionar_coberturas(dict(registro,grupo_atividade='ESCRITORIO'))[TERCEIROS]
    b = motor.dimensionar_coberturas(dict(registro,grupo_atividade='CLINICA'))[TERCEIROS]
    assert a['faixa_valor_min'] == b['faixa_valor_min'] is None
    assert a['fator_impacto']['confianca'] == b['fator_impacto']['confianca'] == 0


def test_ausencia_territorial_reduz_confianca_sem_zerar(registro):
    motor = MotorPontuacao()
    a = motor.analisar_registro(registro)[ROUBO]
    b = motor.analisar_registro(dict(registro,seguranca_da_cidade_0_1=None))[ROUBO]
    assert b['confianca'] < a['confianca']
    assert not b['risco_evento_observado']
    assert b['prioridade'] > 0
    assert b['prioridade_max'] - b['prioridade_min'] >= a['prioridade_max'] - a['prioridade_min']


def test_receita_empresa_nao_e_dividida_entre_unidades(registro):
    v = MotorPontuacao().analisar_registro(dict(registro,quantidade_unidades=2))[ROUBO]
    assert v['fator_vulnerabilidade']['confianca'] == 0
    assert v['fator_vulnerabilidade']['valor_original'] is None


def test_custos_nao_somam_aluguel_e_folha_novamente(registro, config):
    s = MotorPontuacao().dimensionar_coberturas(registro)[DESPESAS]
    assert s['faixa_valor_min'] == registro['despesa_fixa_mensal_estimada']
    assert s['faixa_valor_max'] == registro['despesa_fixa_mensal_estimada'] * config['cenarios']['meses_paralisacao_max']


def test_ausencia_aluguel_nao_prova_imovel_proprio(registro):
    s = MotorPontuacao().dimensionar_coberturas(dict(registro,valor_aluguel_recorrente=0,pagamento_aluguel_recorrente='NAO'))[ALUGUEL]
    assert s['faixa_valor_min'] is None
    assert s['fator_impacto']['confianca'] == 0
    assert 'prioridade' not in s


def test_estoque_pico_e_cenario_sem_soma_duplicada(registro):
    s = MotorPontuacao().analisar_registro(registro)[ROUBO]
    assert s['valor_exposto_brl'] == registro['bens_ponderados'] + registro['estoque_medio_estimado']
    assert s['faixa_valor_max'] == registro['bens_total_referencia'] + registro['estoque_pico_estimado']


def test_quatro_indices_nove_dimensionamentos_com_limites(registro):
    pontos = MotorPontuacao().analisar_registro(registro)
    assert set(pontos) == set(DECISORIAS)
    dimensoes=MotorPontuacao().dimensionar_coberturas(registro)
    assert len(dimensoes)==9
    assert all('prioridade' not in d for d in dimensoes.values())
    for s in pontos.values():
        assert 0 <= s['prioridade_min'] <= s['prioridade'] <= s['prioridade_max'] <= 100
        d = s['decomposicao']
        assert math.isclose(d['base_pontos']+d['interacao_pontos']+d['efeito_limite_pontos'],s['prioridade'],abs_tol=.0001)
        assert 0 <= s['confianca'] <= 1


@pytest.mark.parametrize('valor',[0,30000,3000000,1e100])
def test_normalizacao_limitada_preserva_ordem(valor):
    n = normalizar_financeiro(valor,3000000)
    assert 0 <= n <= 1
    assert normalizar_financeiro(-1,3000000) is None


@pytest.mark.parametrize('cobertura',[ROUBO,VENDAVAL])
def test_monotonicidade_financeira_cenarios_contrastantes(registro,cobertura):
    motor = MotorPontuacao()
    notas = []
    for fator in [.1,1,10,100]:
        r = copy.deepcopy(registro)
        for campo in ['bens_ponderados','bens_total_referencia','equipamentos_ponderados',
                      'equipamentos_total_referencia','despesa_fixa_mensal_estimada']:
            r[campo] *= fator
        notas.append(motor.analisar_registro(r)[cobertura]['prioridade'])
    assert notas == sorted(notas)


@pytest.mark.parametrize('mudanca',[lambda c:c['coberturas'][ROUBO]['pesos_evento'].update(exposicao_territorial=-1),
    lambda c:c['modelo'].update(piso_evento=float('nan')),
    lambda c:c['normalizacao'].update(bens=0),
    lambda c:c['planos'].update(limiar_cobertura=120),
    lambda c:c['materiais'].update(ALVENARIA=2)])
def test_config_invalida_rejeitada(config,mudanca):
    mudanca(config)
    with pytest.raises(ValueError):
        carregar_config(config)


def test_local_tem_mais_influencia_sem_confundir_com_patrimonio(registro):
    motor=MotorPontuacao()
    pequeno=motor.analisar_registro(dict(registro,bens_ponderados=30000,estoque_medio_estimado=0,
        seguranca_da_cidade_0_1=.1))[ROUBO]
    grande=motor.analisar_registro(dict(registro,bens_ponderados=3000000,estoque_medio_estimado=0,
        seguranca_da_cidade_0_1=.9))[ROUBO]
    assert pequeno['risco_evento_relativo']>grande['risco_evento_relativo']
    assert pequeno['prioridade']>grande['prioridade']
    assert grande['prioridade']>0


def test_confianca_territorial_nao_altera_perigo_observado(registro):
    motor=MotorPontuacao()
    a=motor.analisar_registro(dict(registro,confianca_seguranca_0_1=.2))[ROUBO]
    b=motor.analisar_registro(dict(registro,confianca_seguranca_0_1=.8))[ROUBO]
    assert a['prioridade']==b['prioridade']
    assert a['risco_evento_relativo']==b['risco_evento_relativo']
    assert a['confianca']<b['confianca']


def test_nr4_afeta_evento_sem_multiplicar_folha_por_funcionarios(registro):
    motor=MotorPontuacao()
    a=motor.analisar_registro(dict(registro,grau_risco_nr4=1))[EMPREGADOR]
    b=motor.analisar_registro(dict(registro,grau_risco_nr4=3))[EMPREGADOR]
    assert a['prioridade']<b['prioridade']
    assert a['impacto_normalizado']==b['impacto_normalizado']
    c=motor.analisar_registro(dict(registro,grau_risco_nr4=3,quantidade_funcionarios_estimada=10000))[EMPREGADOR]
    assert b['prioridade']==c['prioridade']


def test_funcionarios_empresa_nao_sao_atribuidos_a_filial(registro):
    motor=MotorPontuacao()
    f=motor.fatores(dict(registro,quantidade_unidades=2))['funcionarios']
    assert f.confianca==0


def test_vidros_confirmados_e_ausencia_explicita(registro):
    motor=MotorPontuacao()
    a=motor.analisar_registro(dict(registro,possui_vidros_confirmado='SIM',valor_vidros_reposicao_brl=10000))[VIDROS]
    b=motor.analisar_registro(dict(registro,possui_vidros_confirmado='SIM',valor_vidros_reposicao_brl=100000))[VIDROS]
    assert b['prioridade']>a['prioridade'] and a['faixa_valor_min']==10000
    sem=motor.analisar_registro(dict(registro,possui_vidros_confirmado='NAO'))[VIDROS]
    assert sem['prioridade_min']==sem['prioridade']==sem['prioridade_max']==0
