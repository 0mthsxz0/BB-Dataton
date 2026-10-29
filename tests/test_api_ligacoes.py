import io
from unittest.mock import MagicMock

import pytest

from scripts import api_ligacoes
from ligacoes import Configuracao, criar_twiml


@pytest.mark.parametrize('publicado', ['correto', 'indisponivel', 'outro-texto'])
def test_trial_confere_texto_publico_antes_de_ligar(monkeypatch, tmp_path, publicado):
    monkeypatch.setenv('BB_VOICE_PLAYBACK', 'say')
    monkeypatch.setenv('BB_ROTEIROS_DIR', str(tmp_path))
    config = Configuracao('AC' + 'b' * 32, 'c' * 32,
                         twiml_url='https://exemplo.test/voz.xml')
    monkeypatch.setattr(api_ligacoes.Configuracao, 'do_ambiente', lambda: config)
    mensagem = 'Olá, esta é a mensagem aprovada no painel.'
    rede = MagicMock()
    if publicado == 'indisponivel':
        rede.side_effect = OSError('502')
    else:
        xml = criar_twiml(mensagem if publicado == 'correto' else 'Outro roteiro')
        rede.return_value.__enter__.return_value = io.BytesIO(xml.encode('utf-8'))
    monkeypatch.setattr(api_ligacoes, 'urlopen', rede)
    cliente = MagicMock()
    cliente.return_value.ligar.return_value = {'sid': 'CA' + 'a' * 32, 'status': 'queued'}
    monkeypatch.setattr(api_ligacoes, 'ClienteLigacoes', cliente)
    pedido = {'action': 'ligar', 'phone': '+5561999999999', 'text': mensagem}
    if publicado == 'correto':
        assert api_ligacoes.executar(pedido)['status'] == 'queued'
        cliente.return_value.ligar.assert_called_once_with(pedido['phone'])
        assert '/voz/' in cliente.call_args.args[0].twiml_url
    else:
        with pytest.raises(ValueError, match='Nenhuma ligação foi enviada'):
            api_ligacoes.executar(pedido)
        cliente.assert_not_called()
