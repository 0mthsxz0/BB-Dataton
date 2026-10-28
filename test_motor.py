import copy
import math
import pytest
from motor_pontuacao import (MotorPontuacao, ROUBO, ELETRICO, INCENDIO, VIDROS,
    CIBER, DESPESAS, ALUGUEL, TERCEIROS, carregar_config, normalizar_financeiro)


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


def test_aumentar_equipamentos_afeta_danos_eletricos(registro):
    motor = MotorPontuacao()
    a = motor.analisar_registro(registro)[ELETRICO]
    b = motor.analisar_registro(dict(registro,equipamentos_ponderados=300000))[ELETRICO]
    assert b['prioridade'] > a['prioridade']


def test_dependencia_digital_aumenta_impacto_e_prioridade(registro):
    motor = MotorPontuacao()
    a = motor.analisar_registro(dict(registro,dependencia_digital_pct=10))[CIBER]
    b = motor.analisar_registro(dict(registro,dependencia_digital_pct=95))[CIBER]
    assert b['prioridade'] > a['prioridade']


def test_maturidade_nao_e_vulnerabilidade_cibernetica(registro):
    motor = MotorPontuacao()
    assert motor.analisar_registro(dict(registro,indice_maturidade_digital=0))[CIBER] == motor.analisar_registro(dict(registro,indice_maturidade_digital=100))[CIBER]


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
    a = motor.analisar_registro(dict(registro,grupo_atividade='ESCRITORIO'))[TERCEIROS]
    b = motor.analisar_registro(dict(registro,grupo_atividade='CLINICA'))[TERCEIROS]
    assert a['impacto_normalizado'] == b['impacto_normalizado']
    assert a['fator_impacto']['confianca'] == b['fator_impacto']['confianca'] == 0
    assert a['risco_evento_relativo'] < b['risco_evento_relativo']


def test_ausencia_territorial_reduz_confianca_sem_zerar(registro):
    motor = MotorPontuacao()
    a = motor.analisar_registro(registro)[ROUBO]
    b = motor.analisar_registro(dict(registro,seguranca_da_cidade_0_1=None))[ROUBO]
    assert b['confianca'] < a['confianca']
    assert not b['risco_evento_observado']
    assert b['prioridade'] > 0
    assert b['prioridade_max'] - b['prioridade_min'] >= a['prioridade_max'] - a['prioridade_min']


def test_receita_empresa_nao_e_dividida_entre_unidades(registro):
    v = MotorPontuacao().analisar_registro(dict(registro,quantidade_unidades=2))[DESPESAS]
    assert v['fator_vulnerabilidade']['confianca'] == 0
    assert v['fator_vulnerabilidade']['valor_original'] is None


def test_custos_nao_somam_aluguel_e_folha_novamente(registro, config):
    s = MotorPontuacao().analisar_registro(registro)[DESPESAS]
    assert s['faixa_valor_min'] == registro['despesa_fixa_mensal_estimada']
    assert s['faixa_valor_max'] == registro['despesa_fixa_mensal_estimada'] * config['cenarios']['meses_paralisacao_max']


def test_ausencia_aluguel_nao_prova_imovel_proprio(registro):
    s = MotorPontuacao().analisar_registro(dict(registro,valor_aluguel_recorrente=0,pagamento_aluguel_recorrente='NAO'))[ALUGUEL]
    assert s['faixa_valor_min'] is None
    assert s['fator_impacto']['confianca'] == 0
    assert s['prioridade'] > 0


def test_estoque_pico_e_cenario_sem_soma_duplicada(registro):
    s = MotorPontuacao().analisar_registro(registro)[ROUBO]
    assert s['valor_exposto_brl'] == registro['bens_ponderados'] + registro['estoque_medio_estimado']
    assert s['faixa_valor_max'] == registro['bens_total_referencia'] + registro['estoque_pico_estimado']


def test_nove_coberturas_e_adicional_com_limites_e_decomposicao(registro):
    pontos = MotorPontuacao().analisar_registro(registro)
    assert len(pontos) == 10
    assert sum(not s['adicional'] for s in pontos.values()) == 9
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


@pytest.mark.parametrize('cobertura',['INCENDIO_RAIO_EXPLOSAO_FUMACA','DANOS_ELETRICOS','DESPESAS_FIXAS',ROUBO])
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
