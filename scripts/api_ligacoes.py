"""Adaptador JSON entre o painel Node e o código Twilio da branch codigo-ligacao."""
import json
from dataclasses import replace
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ligacoes import ClienteLigacoes, Configuracao, ErroLigacao, ResultadoIncerto
from roteiros_voz import salvar_roteiro, url_roteiro

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
        roteiro = salvar_roteiro(mensagem)
        config = replace(config, twiml_url=url_roteiro(config.twiml_url, roteiro))
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
