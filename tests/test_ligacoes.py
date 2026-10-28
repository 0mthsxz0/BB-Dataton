import base64
import io
import json
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs
from xml.etree.ElementTree import fromstring

import pytest

from ligacoes import (ClienteLigacoes, Configuracao, ErroLigacao, ResultadoIncerto,
                      SemRedirecionamento, criar_twiml, validar_telefone)

SID = "CA" + "a" * 32
CONTA = "AC" + "b" * 32
TOKEN = "c" * 32


@pytest.fixture
def cliente():
    cliente = ClienteLigacoes(Configuracao(CONTA, TOKEN, "+5511999999999"))
    cliente._opener = MagicMock()
    return cliente


def resposta(cliente, status="queued"):
    conteudo = {"sid": SID, "status": status, "duration": "0", "to": "privado"}
    cliente._opener.open.return_value.__enter__.return_value = io.BytesIO(json.dumps(conteudo).encode())


def test_contrato_http_e_texto_escapado(cliente):
    resposta(cliente)
    mensagem = 'Olá & <Dial>+5511888888888</Dial> "teste"'
    resultado = cliente.ligar("+5511888888888", mensagem, 60)
    req = cliente._opener.open.call_args.args[0]
    assert req.full_url == f"https://api.twilio.com/2010-04-01/Accounts/{CONTA}/Calls.json"
    assert req.get_method() == "POST"
    assert req.get_header("Authorization") == "Basic " + base64.b64encode(f"{CONTA}:{TOKEN}".encode()).decode()
    dados = parse_qs(req.data.decode())
    assert dados["To"] == ["+5511888888888"]
    assert dados["From"] == ["+5511999999999"]
    assert dados["TimeLimit"] == ["60"]
    assert dados["Timeout"] == ["30"]
    xml = fromstring(dados["Twiml"][0])
    assert xml.find("Say").text == mensagem
    assert xml.find("Say").attrib == {"voice": "Polly.Camila", "language": "pt-BR"}
    assert xml.find("Dial") is None
    assert xml.find("Hangup") is not None
    assert "to" not in resultado
    assert cliente._opener.open.call_args.kwargs["timeout"] == 20


@pytest.mark.parametrize("numero", ["11999999999", "+05511999999999", "+55 11999999999", "+1234567890123456", "", "+５５１１９９９９９９９９９"])
def test_rejeita_numero_antes_da_rede(cliente, numero):
    with pytest.raises(ValueError):
        cliente.ligar(numero, "Olá")
    cliente._opener.open.assert_not_called()


@pytest.mark.parametrize("mensagem", ["", "  ", "a" * 1501, "a\x00b", "&" * 1500])
def test_rejeita_mensagem_antes_da_rede(cliente, mensagem):
    with pytest.raises(ValueError):
        cliente.ligar("+5511888888888", mensagem)
    cliente._opener.open.assert_not_called()


@pytest.mark.parametrize("limite", [0, 9, 601, True, 10.5])
def test_rejeita_limite(cliente, limite):
    with pytest.raises(ValueError):
        cliente.ligar("+5511888888888", "Olá", limite)
    cliente._opener.open.assert_not_called()


def test_consulta_e_encerramento(cliente):
    resposta(cliente, "in-progress")
    cliente.consultar(SID)
    req = cliente._opener.open.call_args.args[0]
    assert req.get_method() == "GET"
    assert req.full_url.endswith(f"/Calls/{SID}.json")
    resposta(cliente, "completed")
    assert cliente.encerrar(SID)["status"] == "completed"
    req = cliente._opener.open.call_args.args[0]
    assert parse_qs(req.data.decode()) == {"Status": ["completed"]}
    with pytest.raises(ValueError):
        cliente.consultar("../outra-conta")


def test_erro_trial_sem_vazamento(cliente):
    cliente._opener.open.side_effect = HTTPError("url", 400, "Bad", {},
        io.BytesIO(json.dumps({"code": 21219, "message": TOKEN + " telefone privado"}).encode()))
    with pytest.raises(ErroLigacao, match="verifique o destino") as erro:
        cliente.ligar("+5511888888888", "Olá")
    assert TOKEN not in str(erro.value)


@pytest.mark.parametrize("falha", [URLError("credencial privada"), TimeoutError(),
    HTTPError("url", 503, "Bad", {}, io.BytesIO(b"{}"))])
def test_envio_incerto_nao_repete(cliente, falha):
    cliente._opener.open.side_effect = falha
    with pytest.raises(ResultadoIncerto):
        cliente.ligar("+5511888888888", "Olá")
    assert cliente._opener.open.call_count == 1


def test_resposta_invalida_e_configuracao_sem_token_no_repr(cliente, monkeypatch):
    cliente._opener.open.return_value.__enter__.return_value = io.BytesIO(b"[]")
    with pytest.raises(ResultadoIncerto):
        cliente.ligar("+5511888888888", "Olá")
    assert TOKEN not in repr(cliente.config)
    for nome in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"):
        monkeypatch.delenv(nome, raising=False)
    with pytest.raises(ValueError, match="Configure no servidor"):
        Configuracao.do_ambiente()
    assert SemRedirecionamento().redirect_request(None, None, 302, "", {}, "https://outro.site") is None
