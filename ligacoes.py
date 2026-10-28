"""Chamadas de voz pela API Twilio. Não realiza chamadas na importação."""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
import json
from http.client import HTTPException
import os
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree.ElementTree import Element, SubElement, tostring

TEMPLATE_TRIAL = "https://webhooks.twilio.com/v1/Voice/Template/voice_text_to_speech"


class ErroLigacao(Exception):
    """Erro seguro para exibição, sem credenciais ou resposta bruta da API."""


class ResultadoIncerto(ErroLigacao):
    """O envio pode ter sido aceito; não repetir automaticamente."""


def validar_telefone(numero: str) -> str:
    numero = numero.strip()
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", numero):
        raise ValueError("Use o formato internacional: +, país, DDD e número, sem espaços.")
    return numero


def criar_twiml(mensagem: str) -> str:
    mensagem = mensagem.strip()
    if not 1 <= len(mensagem) <= 1500:
        raise ValueError("A mensagem deve ter entre 1 e 1500 caracteres.")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in mensagem):
        raise ValueError("A mensagem contém caracteres de controle inválidos.")
    resposta = Element("Response")
    SubElement(resposta, "Say", voice="Polly.Camila", language="pt-BR").text = mensagem
    SubElement(resposta, "Hangup")
    xml = tostring(resposta, encoding="unicode")
    if len(xml) > 4000:
        raise ValueError("A mensagem excede o limite de 4000 caracteres após a conversão para XML. Reduza o texto.")
    return xml


@dataclass(frozen=True)
class Configuracao:
    conta: str
    token: str = field(repr=False)
    origem: str = ""
    modo: str = "trial"

    def __post_init__(self):
        if not re.fullmatch(r"AC[0-9a-fA-F]{32}", self.conta):
            raise ValueError("TWILIO_ACCOUNT_SID deve ser o Account SID iniciado por AC.")
        if not re.fullmatch(r"[0-9a-fA-F]{32}", self.token):
            raise ValueError("TWILIO_AUTH_TOKEN deve conter o Auth Token da conta.")
        if self.modo not in {"trial", "completo"}:
            raise ValueError("TWILIO_MODE deve ser trial ou completo.")
        if self.modo == "completo":
            if not self.origem:
                raise ValueError("Configure TWILIO_FROM_NUMBER para o modo completo.")
            validar_telefone(self.origem)

    @classmethod
    def do_ambiente(cls):
        nomes = ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN")
        valores = [os.environ.get(nome, "").strip() for nome in nomes]
        faltantes = [nome for nome, valor in zip(nomes, valores) if not valor]
        if faltantes:
            raise ValueError("Configure no servidor: " + ", ".join(faltantes))
        return cls(*valores, origem=os.environ.get("TWILIO_FROM_NUMBER", "").strip(),
                   modo=os.environ.get("TWILIO_MODE", "trial").strip().lower())


class SemRedirecionamento(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Nunca encaminhar Authorization para outra URL.
        return None


class ClienteLigacoes:
    def __init__(self, config: Configuracao):
        self.config = config
        self._opener = build_opener(SemRedirecionamento())

    def _mensagem_segura(self, mensagem):
        """Expõe a explicação do provedor sem mostrar credenciais ou telefones."""
        if not isinstance(mensagem, str):
            return ""
        mensagem = mensagem.replace(self.config.token, "[token oculto]")
        mensagem = mensagem.replace(self.config.conta, "[conta oculta]")
        credencial = base64.b64encode(
            f"{self.config.conta}:{self.config.token}".encode()).decode()
        mensagem = mensagem.replace(credencial, "[credencial oculta]")
        mensagem = re.sub(r"https?://\S+", "[link omitido]", mensagem)
        mensagem = re.sub(r"\b(?:AC|SK|CA)?[0-9a-fA-F]{32}\b", "[identificador oculto]", mensagem)
        mensagem = re.sub(r"(?<!\w)\+?[0-9][0-9 ()-]{6,}[0-9](?!\w)", "[telefone oculto]", mensagem)
        return " ".join(mensagem.split())[:600]

    def _requisicao(self, sufixo="", dados=None):
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.config.conta}/Calls{sufixo}.json"
        credencial = base64.b64encode(
            f"{self.config.conta}:{self.config.token}".encode()).decode()
        req = Request(url, data=urlencode(dados).encode() if dados is not None else None,
                      headers={"Authorization": "Basic " + credencial,
                               "Content-Type": "application/x-www-form-urlencoded",
                               "Accept": "application/json"})
        try:
            with self._opener.open(req, timeout=20) as resposta:
                resultado = json.load(resposta)
            if not isinstance(resultado, dict) or not re.fullmatch(
                    r"CA[0-9a-fA-F]{32}", str(resultado.get("sid", ""))):
                raise ValueError("Resposta inesperada")
            return {k: resultado.get(k) for k in ("sid", "status", "duration")}
        except HTTPError as erro:
            detalhe = ""
            try:
                corpo = json.loads(erro.read())
                codigo = corpo.get("code")
                detalhe = self._mensagem_segura(corpo.get("message"))
                if isinstance(codigo, str) and codigo.isascii() and codigo.isdigit():
                    codigo = int(codigo)
            except (ValueError, AttributeError):
                codigo = None
            mensagens = {
                20003: "Credenciais inválidas ou sem acesso à conta.",
                21211: "O telefone de destino foi rejeitado pela Twilio.",
                21212: "Confira o número de origem autorizado na Twilio.",
                21215: "Confira as permissões geográficas de Voice no console.",
                21219: "No teste grátis, verifique o destino no console da Twilio.",
                21210: "O número de origem precisa ser autorizado pela Twilio.",
                20404: "Chamada não encontrada nesta conta.",
                20429: "Limite de requisições atingido. Aguarde antes de tentar novamente.",
            }
            if erro.code >= 500:
                raise ResultadoIncerto("A Twilio falhou ao responder. Consulte o console antes de repetir o envio.") from None
            codigo_seguro = str(codigo) if isinstance(codigo, int) else "indisponível"
            explicacao = mensagens.get(codigo)
            if explicacao is None:
                explicacao = f"Twilio recusou a operação (HTTP {erro.code}, código {codigo_seguro})."
                explicacao += " Detalhe da Twilio: " + detalhe if detalhe else " Confira os logs de Voice no console."
            raise ErroLigacao(explicacao) from None
        except (URLError, TimeoutError, socket.timeout, OSError, ValueError, HTTPException):
            raise ResultadoIncerto(
                "Não foi possível confirmar a resposta. Consulte os logs de Voice no console antes de repetir o envio.") from None

    def ligar(self, destino: str, mensagem: str = "", limite: int | None = None):
        destino = validar_telefone(destino)
        if self.config.modo == "trial":
            if mensagem.strip() or limite is not None:
                raise ValueError("No modo trial, use a demonstração da Twilio sem mensagem ou duração personalizada.")
            # O trial escolhe a origem. From, Twiml, TimeLimit e Timeout são
            # parâmetros da API completa e não devem seguir nesta requisição.
            return self._requisicao(dados={"To": destino, "Url": TEMPLATE_TRIAL})
        if limite is None:
            limite = 120
        if type(limite) is not int or not 10 <= limite <= 600:
            raise ValueError("O limite da chamada deve ser de 10 a 600 segundos.")
        twiml = criar_twiml(mensagem)
        return self._requisicao(dados={"To": destino, "From": self.config.origem,
            "Twiml": twiml, "TimeLimit": limite, "Timeout": 30})

    def consultar(self, sid: str):
        return self._requisicao("/" + self._validar_sid(sid))

    def encerrar(self, sid: str):
        # completed também encerra chamadas ainda tocando; não depende de GET prévio.
        return self._requisicao("/" + self._validar_sid(sid), {"Status": "completed"})

    @staticmethod
    def _validar_sid(sid):
        if not re.fullmatch(r"CA[0-9a-fA-F]{32}", sid):
            raise ValueError("Call SID inválido.")
        return sid
