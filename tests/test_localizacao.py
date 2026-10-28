from pathlib import Path
from unittest.mock import Mock
import pytest
import requests
from localizacao import consultar_cep, aplicar_localizacao
from motor_pontuacao import MotorPontuacao, ROUBO, VENDAVAL


def payload():
    return {'cep': '01001-000', 'localidade': 'São Paulo', 'uf': 'SP',
            'ibge': '3550308', 'bairro': 'Sé', 'logradouro': 'Praça da Sé'}


@pytest.mark.parametrize('cep', ['123', 'abcdefgh', '010010000', '01001/000', ''])
def test_cep_invalido_nao_consulta_rede(cep, monkeypatch):
    get = Mock()
    monkeypatch.setattr('localizacao.requests.get', get)
    with pytest.raises(ValueError):
        consultar_cep(cep)
    get.assert_not_called()


def test_consulta_validada(monkeypatch):
    get = Mock(return_value=Mock(json=payload))
    monkeypatch.setattr('localizacao.requests.get', get)
    local = consultar_cep('01001-000')
    assert local['codigo_ibge_municipio'] == '3550308'
    assert local['bairro'] == 'Sé'
    get.assert_called_once_with('https://viacep.com.br/ws/01001000/json/', timeout=(4, 10))


@pytest.mark.parametrize('dados', [{'erro': True}, [], {},
    dict(payload(), cep='20040-020'), dict(payload(), ibge='')])
def test_respostas_invalidas(dados, monkeypatch):
    monkeypatch.setattr('localizacao.requests.get', Mock(return_value=Mock(json=lambda: dados)))
    with pytest.raises(ValueError):
        consultar_cep('01001000')


def test_timeout_tratado(monkeypatch):
    monkeypatch.setattr('localizacao.requests.get', Mock(side_effect=requests.Timeout()))
    with pytest.raises(ValueError, match='Tente novamente'):
        consultar_cep('01001000')


def test_troca_sem_herdar_risco(registro, tmp_path):
    original = dict(registro, exposicao_climatica_0_1=.9, fonte_clima='Anterior')
    local = {'codigo_ibge_municipio': '9999999', 'municipio_real': 'Sem referência', 'uf_real': 'SP'}
    novo, avisos = aplicar_localizacao(original, local, tmp_path)
    assert len(avisos) == 2
    for campo in ['seguranca_da_cidade_0_1', 'exposicao_climatica_0_1',
                  'confianca_territorial_0_1', 'fonte_clima']:
        assert novo.get(campo) is None
    assert novo['bens_ponderados'] == original['bens_ponderados']
    assert original['fonte_clima'] == 'Anterior'


def test_vincula_referencias_reais(registro, config):
    pasta = Path(__file__).resolve().parents[1] / 'references'
    local = {'codigo_ibge_municipio': '3550308', 'municipio_real': 'São Paulo', 'uf_real': 'SP'}
    novo, avisos = aplicar_localizacao(registro, local, pasta)
    assert not avisos
    assert novo['granularidade_seguranca'] == novo['granularidade_clima'] == 'MUNICIPIO'
    motor = MotorPontuacao(None, config)
    pontos = motor.analisar_registro(novo)
    assert pontos[ROUBO]['risco_evento_relativo'] == pytest.approx(1-float(novo['seguranca_da_cidade_0_1']))
    assert pontos[VENDAVAL]['risco_evento_relativo'] == pytest.approx(float(novo['exposicao_climatica_0_1']))
    assert pontos[ROUBO]['valor_exposto_brl'] == motor.analisar_registro(registro)[ROUBO]['valor_exposto_brl']
