from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen
from xml.etree.ElementTree import fromstring

import pytest

from roteiros_voz import DURACAO_ROTEIRO, RoteiroExpirado, ler_roteiro, salvar_roteiro, url_roteiro
import roteiros_voz


def test_audio_publico_tem_mesmo_id_e_expiracao(monkeypatch, tmp_path):
    monkeypatch.setenv('BB_ROTEIROS_DIR', str(tmp_path))
    def sintetizar(texto, destino):
        assert texto == 'Mensagem aprovada'
        destino.write_bytes(b'RIFF-audio-teste')
    monkeypatch.setattr(roteiros_voz, 'gerar_audio', sintetizar)
    id = salvar_roteiro('Mensagem aprovada', audio_base='https://exemplo.test/voz.xml')
    xml = fromstring(ler_roteiro(id))
    assert xml.find('Say') is None
    assert xml.find('Play').text == f'https://exemplo.test/voz/{id}.wav'
    servidor = criar_servidor(0)
    thread = Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f'http://127.0.0.1:{servidor.server_port}/voz/{id}.wav', timeout=3) as resposta:
            assert resposta.headers['Content-Type'] == 'audio/wav'
            assert resposta.read() == b'RIFF-audio-teste'
        monkeypatch.setattr(roteiros_voz.time, 'time', lambda: 2_000_000_000)
        with pytest.raises(HTTPError) as erro:
            urlopen(f'http://127.0.0.1:{servidor.server_port}/voz/{id}.wav', timeout=3)
        assert erro.value.code == 410
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=3)
from servidor_voz import criar_servidor


def test_roteiros_independentes_e_expiracao(monkeypatch, tmp_path):
    monkeypatch.setenv('BB_ROTEIROS_DIR', str(tmp_path))
    a = salvar_roteiro('Cliente A & seus dados', agora=100)
    b = salvar_roteiro('Cliente B', agora=101)
    assert a != b
    assert fromstring(ler_roteiro(a, agora=102)).find('Say').text == 'Cliente A & seus dados'
    assert fromstring(ler_roteiro(b, agora=102)).find('Say').text == 'Cliente B'
    with pytest.raises(RoteiroExpirado):
        ler_roteiro(a, agora=100 + DURACAO_ROTEIRO)
    with pytest.raises(FileNotFoundError):
        ler_roteiro('../cliente')
    assert url_roteiro('https://site.ngrok-free.dev/voz.xml', a).endswith(f'/voz/{a}.xml')


def test_http_entrega_snapshot_e_rejeita_expirado(monkeypatch, tmp_path):
    monkeypatch.setenv('BB_ROTEIROS_DIR', str(tmp_path / 'roteiros'))
    atual = salvar_roteiro('Mensagem revisada')
    expirado = salvar_roteiro('Não deve ser lida', agora=0)
    arquivo = tmp_path / 'mensagem.txt'
    arquivo.write_text('Mensagem compartilhada diferente', encoding='utf-8')
    servidor = criar_servidor(0, arquivo)
    thread = Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{servidor.server_port}'
    try:
        with urlopen(url + f'/voz/{atual}.xml', timeout=3) as resposta:
            assert fromstring(resposta.read()).find('Say').text == 'Mensagem revisada'
        for caminho, status in [(f'/voz/{expirado}.xml', 410), ('/voz/' + '0'*64 + '.xml', 404),
                                 ('/voz/../../.env', 404)]:
            with pytest.raises(HTTPError) as erro:
                urlopen(url + caminho, timeout=3)
            assert erro.value.code == status
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=3)


@pytest.mark.parametrize('url', ['https://site/outro.xml', 'http://site/voz.xml',
                                'https://user:pass@site/voz.xml', 'https://site/voz.xml?q=1'])
def test_url_incompativel_nao_gera_endereco_ambiguo(url):
    with pytest.raises(ValueError):
        url_roteiro(url, 'a' * 64)
