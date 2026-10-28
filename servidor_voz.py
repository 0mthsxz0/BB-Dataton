"""Entrega somente o roteiro de voz; não faz chamadas nem publica o servidor."""
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import urlsplit

from ligacoes import criar_twiml
from roteiros_voz import PADRAO_ID, RoteiroExpirado, ler_roteiro

ARQUIVO_MENSAGEM = Path(__file__).with_name("mensagem_ligacao.txt")


class ServidorHTTP(ThreadingHTTPServer):
    daemon_threads = True

    def get_request(self):
        conexao, endereco = super().get_request()
        conexao.settimeout(5)
        return conexao, endereco


class RoteiroHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, arquivo=ARQUIVO_MENSAGEM, **kwargs):
        self.arquivo = Path(arquivo)
        super().__init__(*args, **kwargs)

    def responder(self):
        caminho = urlsplit(self.path).path
        roteiro = re.fullmatch(r"/voz/(" + PADRAO_ID + r")\.xml", caminho)
        if caminho != "/voz.xml" and not roteiro:
            self.send_error(404)
            return
        try:
            if roteiro:
                conteudo = ler_roteiro(roteiro.group(1)).encode("utf-8")
            else:
                # A rota de demonstração continua relendo o TXT.
                with self.arquivo.open(encoding="utf-8-sig") as arquivo:
                    mensagem = arquivo.read(1502)
                conteudo = criar_twiml(mensagem).encode("utf-8")
        except RoteiroExpirado:
            self.send_error(410, "Roteiro expirado")
            return
        except FileNotFoundError:
            self.send_error(404, "Roteiro nao encontrado")
            return
        except (OSError, ValueError):
            conteudo = b"Roteiro indisponivel. Confira mensagem_ligacao.txt no servidor."
            self.send_response(503)
            tipo = "text/plain; charset=utf-8"
        else:
            self.send_response(200)
            tipo = "application/xml; charset=utf-8"
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(conteudo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(conteudo)
        self.close_connection = True

    do_GET = responder
    do_POST = responder

    def log_message(self, format, *args):
        # Não registrar números, query strings ou corpo enviado pelo provedor.
        pass


def criar_servidor(porta=8765, arquivo=ARQUIVO_MENSAGEM):
    return ServidorHTTP(("127.0.0.1", porta), partial(RoteiroHandler, arquivo=arquivo))


if __name__ == "__main__":
    with criar_servidor() as servidor:
        print("Roteiro local: http://127.0.0.1:8765/voz.xml")
        print("Edite mensagem_ligacao.txt. Para encerrar, pressione Ctrl+C.")
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            pass
