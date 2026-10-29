"""API local por empresa-estabelecimento, reutilizando a exportação do motor."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, HTTPServer
import hmac
import json
import socket

from exportacao import analisar_base
from motor_pontuacao import carregar_config
from processamento import carregar_base
from produto import REGRAS

VERSION = 'templates-1.0'
ENDPOINT = '/api/templates/recomendacao'


class ServicoTemplates:
    def __init__(self, dados, config=None, data_analise=None, referencias=None):
        self.data_analise = date.fromisoformat(data_analise) if data_analise else date.today()
        self.base = carregar_base(dados, referencias=referencias, data_analise=self.data_analise.isoformat())
        self.config = carregar_config(config)
        self.indices = {(r.empresa_id, r.imovel_id): i for i, r in self.base.estabelecimentos.iterrows()}

    def contrato(self):
        return {'versao_api': VERSION, 'data_analise': self.data_analise.isoformat(),
                'versao_regras': REGRAS['version'], 'estabelecimentos': len(self.indices),
                'colunas': self.base.templates, 'entradas_sha256': self.base.hashes,
                'config_sha256': sha256(json.dumps(self.config, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}

    def recomendar(self, payload):
        if not isinstance(payload, dict) or set(payload) != {'empresa_id', 'imovel_id'}:
            raise ValueError('Envie somente empresa_id e imovel_id em um objeto JSON.')
        if any(not isinstance(v, str) or not v.strip() or len(v) > 100 for v in payload.values()):
            raise ValueError('Identificadores devem ser textos não vazios de até 100 caracteres.')
        chave = payload['empresa_id'], payload['imovel_id']
        if chave not in self.indices:
            raise KeyError('Empresa-estabelecimento não encontrado na base carregada.')
        # A base foi agregada integralmente: quantidade de unidades e sinais da empresa
        # não são recalculados como se a filial consultada fosse a única unidade.
        base_caso = replace(self.base, estabelecimentos=self.base.estabelecimentos.loc[[self.indices[chave]]].copy())
        r, c, auditoria = analisar_base(base_caso, self.config, data_analise=self.data_analise.isoformat())
        def records(df):
            return df.astype(object).where(df.notna(), None).to_dict('records')
        return {'resultado': records(r)[0], 'coberturas': records(c), 'auditoria': auditoria[0],
                'metadados': self.contrato()}


def criar_servidor(servico, token, porta=4180):
    if not isinstance(token, str) or len(token) < 24:
        raise ValueError('Configure um token local com pelo menos 24 caracteres.')

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def log_message(self, *_):
            pass  # Não registrar identificadores nem token no console.

        def responder(self, status, data):
            body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def autorizado(self):
            if self.headers.get('Origin'):
                self.responder(403, {'error': 'Este serviço recebe chamadas locais de integração.'})
                return False
            header = self.headers.get('Authorization', '')
            if not hmac.compare_digest(header.encode(), ('Bearer ' + token).encode()):
                self.responder(401, {'error': 'Token de integração inválido.'})
                return False
            return True

        def do_GET(self):
            if self.path == '/health':
                self.responder(200, {'status': 'ok', 'versao_api': VERSION})
            elif self.path == '/api/templates/contrato':
                if self.autorizado():
                    self.responder(200, servico.contrato())
            else:
                self.responder(404, {'error': 'Rota não encontrada.'})

        def do_POST(self):
            if not self.autorizado():
                return
            if self.path != ENDPOINT:
                self.responder(404, {'error': 'Rota não encontrada.'})
                return
            if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                self.responder(415, {'error': 'Envie application/json.'})
                return
            try:
                if self.headers.get('Transfer-Encoding'):
                    raise ValueError('Use Content-Length.')
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 4096:
                    self.responder(413, {'error': 'Corpo deve conter entre 1 e 4096 bytes.'})
                    return
                payload = json.loads(self.rfile.read(size))
                response = servico.recomendar(payload)
            except KeyError:
                self.responder(404, {'error': 'Empresa-estabelecimento não encontrado.'})
            except (ValueError, UnicodeError):
                self.responder(422, {'error': 'Objeto inválido. Informe somente empresa_id e imovel_id válidos.'})
            except (TimeoutError, socket.timeout):
                self.responder(408, {'error': 'Tempo de envio excedido.'})
            except Exception:
                self.responder(500, {'error': 'Falha no motor. Confira os dados e dependências locais.'})
            else:
                self.responder(200, response)

    return HTTPServer(('127.0.0.1', porta), Handler)
