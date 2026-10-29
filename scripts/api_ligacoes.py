"""Adaptador JSON entre o painel Node e o código Twilio da branch codigo-ligacao."""
import json
import os
from dataclasses import replace
from pathlib import Path
import sys
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ligacoes import ClienteLigacoes, Configuracao, ErroLigacao, ResultadoIncerto
from roteiros_voz import salvar_roteiro, url_roteiro, ler_roteiro


def verificar_roteiro_publico(url, esperado):
    """Confirma o arquivo público antes de iniciar uma chamada cobrada."""
    try:
        pedido = Request(url, headers={'ngrok-skip-browser-warning': '1'})
        with urlopen(pedido, timeout=8) as resposta:
            conteudo = resposta.read(16001).decode('utf-8')
        if conteudo != esperado:
            raise ValueError('Roteiro divergente')
    except Exception:
        raise ValueError(
            'O roteiro de voz não está acessível no endereço público. '
            'Inicie servidor_voz.py na porta 8765, confira o túnel e '
            'TWILIO_TWIML_URL. Nenhuma ligação foi enviada à Twilio.'
        ) from None

def executar(payload):
    if not isinstance(payload, dict) or payload.get('action') != 'ligar':
        raise ValueError('Ação de telefonia inválida.')
    mensagem = payload.get('text')
    telefone = payload.get('phone')
    if not isinstance(mensagem, str) or not isinstance(telefone, str):
        raise ValueError('Telefone e roteiro são obrigatórios.')
    config = Configuracao.do_ambiente()
    if config.modo == 'trial':
        if not config.twiml_url:
            raise ValueError('Configure TWILIO_TWIML_URL pública HTTPS no modo trial.')
        usar_audio = os.name == 'nt' and os.environ.get('BB_VOICE_PLAYBACK', 'audio') == 'audio'
        roteiro = salvar_roteiro(mensagem, audio_base=config.twiml_url if usar_audio else None)
        config = replace(config, twiml_url=url_roteiro(config.twiml_url, roteiro))
        verificar_roteiro_publico(config.twiml_url, ler_roteiro(roteiro))
        result = ClienteLigacoes(config).ligar(telefone)
    else:
        result = ClienteLigacoes(config).ligar(telefone, mensagem)
    return {'sid':result.get('sid'), 'status':result.get('status')}

def main():
    try:
        result = executar(json.load(sys.stdin))
        print(json.dumps({'ok':True,'data':result}))
    except ResultadoIncerto:
        print(json.dumps({'ok':False,'status':503,'error':'Resultado incerto. Verifique os registros da Twilio antes de tentar novamente.'}))
    except (ErroLigacao, ValueError) as exc:
        print(json.dumps({'ok':False,'status':422,'error':str(exc)}))
    except Exception:
        print(json.dumps({'ok':False,'status':503,'error':'Telefonia indisponível. Confira a configuração do servidor.'}))

if __name__=='__main__':
    main()
