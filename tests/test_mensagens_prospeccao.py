import math

import pytest

from mensagens_prospeccao import TEMPLATE_BASE, json_seguro, preencher_template, variaveis_relatorio
from motor_pontuacao import MotorPontuacao
from recomendador import recomendar_plano


def test_template_deriva_do_relatorio_e_preserva_ressalvas(registro, catalogo, config):
    pontos = MotorPontuacao(config=config).analisar_registro(registro)
    plano = recomendar_plano(pontos, catalogo, config, registro)
    variaveis = variaveis_relatorio(registro, pontos, plano, contato='Ana',
        colaborador='João', organizacao='Equipe de teste', empresa='Loja Exemplo')
    mensagem = preencher_template(TEMPLATE_BASE, variaveis)
    assert 'Olá, Ana!' in mensagem
    assert 'Loja Exemplo' in mensagem
    assert 'João' in mensagem
    assert variaveis['plano'] in mensagem
    assert 'preliminar' in mensagem
    assert 'cotação' in mensagem
    assert '{empresa}' not in mensagem
    assert len(mensagem) <= 1500
    for nome in variaveis['coberturas_prioritarias'].split(' e '):
        assert nome
    assert '100000' not in mensagem  # Não expõe faturamento no roteiro padrão.


def test_nao_apresenta_adicional_como_cobertura_do_plano():
    pontos = {'fixa': {'nome': 'Danos elétricos', 'prioridade': 20, 'adicional': False},
              'extra': {'nome': 'Seguro cibernético', 'prioridade': 100, 'adicional': True}}
    plano = {'coberturas': ['fixa'], 'plano_recomendado': 'ESSENCIAL',
             'confianca_geral': .2, 'recomendacao_estavel': False}
    variaveis = variaveis_relatorio({'empresa_id': 'Empresa A'}, pontos, plano)
    assert variaveis['coberturas_prioritarias'] == 'danos elétricos'
    assert 'informações incompletas' in variaveis['ressalvas']
    assert 'pode mudar' in variaveis['ressalvas']


@pytest.mark.parametrize('template', ['{empresa.__class__}', '{ausente}', '{empresa!r}', '{empresa:>100}', '{'])
def test_template_invalido_nao_e_interpretado(template):
    with pytest.raises(ValueError):
        preencher_template(template, {'empresa': 'Loja'})


def test_troca_de_empresa_troca_variaveis_sem_copiar_outro_cliente():
    plano = {'coberturas': [], 'plano_recomendado': 'TOTAL', 'confianca_geral': .9}
    a = preencher_template(TEMPLATE_BASE, variaveis_relatorio({'empresa_id': 'Empresa A'}, {}, plano))
    b = preencher_template(TEMPLATE_BASE, variaveis_relatorio({'empresa_id': 'Empresa B'}, {}, plano))
    assert 'Empresa A' in a and 'Empresa A' not in b
    assert 'Empresa B' in b and 'Empresa B' not in a
    assert json_seguro({'a': math.nan, 'b': math.inf}) == {'a': None, 'b': None}
