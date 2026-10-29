from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import MagicMock
from urllib.parse import parse_qs
from xml.etree.ElementTree import fromstring

import pytest

from ligacoes import ClienteLigacoes, Configuracao
from servidor_voz import criar_servidor


def test_servidor_entrega_apenas_xml_e_rele_roteiro(tmp_path):
    arquivo = tmp_path / "mensagem.txt"
    arquivo.write_text("Olá & obrigado!", encoding="utf-8")
    servidor = criar_servidor(0, arquivo)
    thread = Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{servidor.server_port}"
    try:
        with urlopen(url + "/voz.xml", timeout=3) as resposta:
            xml = fromstring(resposta.read())
            assert xml.find("Say").text == "Olá & obrigado!"
            assert xml.find("Say").attrib["language"] == "pt-BR"
            assert resposta.headers["Content-Type"] == "application/xml; charset=utf-8"
        arquivo.write_text("Nova mensagem", encoding="utf-8")
        with urlopen(Request(url + "/voz.xml", data=b"To=privado"), timeout=3) as resposta:
            assert fromstring(resposta.read()).find("Say").text == "Nova mensagem"
        for caminho in ("/", "/.env", "/../ligacoes.py"):
            with pytest.raises(HTTPError) as erro:
                urlopen(url + caminho, timeout=3)
            assert erro.value.code == 404
        arquivo.write_text("", encoding="utf-8")
        with pytest.raises(HTTPError) as erro:
            urlopen(url + "/voz.xml", timeout=3)
        assert erro.value.code == 503
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=3)


def test_trial_usa_url_customizada_sem_enviar_parametros_completos():
    url = "https://exemplo.trycloudflare.com/voz.xml"
    config = Configuracao("AC" + "b" * 32, "c" * 32, twiml_url=url)
    cliente = ClienteLigacoes(config)
    cliente._requisicao = MagicMock(return_value={"sid": "CA" + "a" * 32})
    cliente.ligar("+5511888888888")
    cliente._requisicao.assert_called_once_with(dados={"To": "+5511888888888", "Url": url})


@pytest.mark.parametrize("url", ["http://site.com/voz", "https://user:pass@site.com/voz", "https://localhost/voz", "https://site.com/#fragmento"])
def test_url_custom_invalida(url):
    with pytest.raises(ValueError):
        Configuracao("AC" + "b" * 32, "c" * 32, twiml_url=url)
