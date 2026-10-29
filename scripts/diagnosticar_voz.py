"""Consulta registros de voz; nunca cria ou altera chamadas."""
import base64
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs
from urllib.request import Request, urlopen
from xml.etree.ElementTree import fromstring

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ligacoes import SemRedirecionamento
from urllib.request import build_opener


def consultar(caminho, conta, token):
    auth = base64.b64encode(f'{conta}:{token}'.encode()).decode()
    pedido = Request(
        f'https://api.twilio.com/2010-04-01/Accounts/{conta}/{caminho}',
        headers={'Authorization': 'Basic ' + auth, 'Accept': 'application/json'})
    with build_opener(SemRedirecionamento()).open(pedido, timeout=15) as resposta:
        return json.load(resposta)


def main():
    conta = os.environ.get('TWILIO_ACCOUNT_SID', '').strip()
    token = os.environ.get('TWILIO_AUTH_TOKEN', '').strip()
    if not re.fullmatch(r'AC[0-9a-fA-F]{32}', conta) or not token:
        print('Execute no mesmo PowerShell em que configurou TWILIO_ACCOUNT_SID e TWILIO_AUTH_TOKEN. Não envie as credenciais no chat.')
        return
    sid = sys.argv[1] if len(sys.argv) > 1 else ''
    if not sid:
        with urlopen('http://127.0.0.1:4040/api/requests/http', timeout=5) as resposta:
            registros = json.load(resposta)['requests']
        for registro in registros:
            if registro['request']['method'] != 'POST':
                continue
            raw = base64.b64decode(registro['request']['raw'])
            corpo = raw.split(b'\r\n\r\n', 1)[-1].decode()
            sid = parse_qs(corpo).get('CallSid', [''])[0]
            if sid:
                break
    if not re.fullmatch(r'CA[0-9a-fA-F]{32}', sid):
        print('Nenhuma chamada encontrada no ngrok. Informe o Call SID após o nome do script.')
        return
    chamada = consultar(f'Calls/{sid}.json', conta, token)
    print('Estado:', chamada.get('status'), '| duração:', chamada.get('duration'), 'segundos')
    for recurso, chave in [('Notifications', 'notifications'), ('Events', 'events')]:
        try:
            dados = consultar(f'Calls/{sid}/{recurso}.json?PageSize=100', conta, token)
        except HTTPError as erro:
            print(recurso, ': consulta indisponível, HTTP', erro.code)
            continue
        itens = dados.get(chave, [])
        print(recurso, ':', len(itens), 'registros')
        for item in itens:
            if recurso == 'Notifications':
                print('Código:', item.get('error_code'), '| nível:', item.get('log'))
                continue
            resposta = item.get('response') or {}
            print('HTTP:', resposta.get('response_code'), '| tipo:', resposta.get('content_type'),
                  '| tempo:', resposta.get('request_duration'))
            try:
                xml = fromstring(resposta.get('response_body') or '')
                for no in xml.iter():
                    if no.tag in {'Say', 'Play', 'Pause', 'Hangup', 'Gather', 'Redirect'}:
                        print('Instrução:', no.tag, '| voz:', no.get('voice'),
                              '| idioma:', no.get('language'), '| caracteres:', len(no.text or ''))
            except (ValueError, TypeError):
                print('Resposta não contém XML válido.')
    print('Consulta encerrada. Nenhuma ligação foi realizada.')


if __name__ == '__main__':
    try:
        main()
    except HTTPError as erro:
        print('A Twilio recusou a consulta. HTTP:', erro.code)
    except (URLError, OSError, ValueError, KeyError):
        print('Não foi possível consultar os registros. Confira as credenciais no terminal e o ngrok local.')
