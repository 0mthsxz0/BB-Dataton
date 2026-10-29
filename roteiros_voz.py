"""Roteiros imutáveis por chamada, locais e com acesso temporário."""
import json
import os
from pathlib import Path
import re
import secrets
import time
from urllib.parse import urlsplit, urlunsplit

from ligacoes import criar_twiml

DURACAO_ROTEIRO = 3600
PADRAO_ID = r"[a-f0-9]{64}"


class RoteiroExpirado(ValueError):
    pass


def pasta_roteiros():
    return Path(os.environ.get("BB_ROTEIROS_DIR") or Path(__file__).parent / "tmp" / "roteiros_voz")


def salvar_roteiro(mensagem, *, agora=None):
    xml = criar_twiml(mensagem)
    instante = time.time() if agora is None else agora
    pasta = pasta_roteiros()
    pasta.mkdir(parents=True, exist_ok=True)
    # Remove somente artefatos próprios expirados, sem percorrer outras pastas.
    for arquivo in pasta.glob("*.json"):
        if re.fullmatch(PADRAO_ID + r"\.json", arquivo.name) and not arquivo.is_symlink():
            try:
                if instante - arquivo.stat().st_mtime > DURACAO_ROTEIRO:
                    arquivo.unlink()
            except FileNotFoundError:
                pass
    identificador = secrets.token_hex(32)
    with (pasta / f"{identificador}.json").open("x", encoding="utf-8") as arquivo:
        json.dump({"criado_em": instante, "xml": xml}, arquivo, ensure_ascii=False)
    return identificador


def ler_roteiro(identificador, *, agora=None):
    if not re.fullmatch(PADRAO_ID, identificador):
        raise FileNotFoundError("Roteiro não encontrado.")
    caminho = pasta_roteiros() / f"{identificador}.json"
    if caminho.is_symlink():
        raise FileNotFoundError("Roteiro não encontrado.")
    with caminho.open(encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    idade = (time.time() if agora is None else agora) - float(dados["criado_em"])
    if not 0 <= idade < DURACAO_ROTEIRO:
        raise RoteiroExpirado("Roteiro expirado.")
    return dados["xml"]


def url_roteiro(url_base, identificador):
    partes = urlsplit(url_base)
    if (partes.scheme != "https" or not partes.hostname or partes.username or partes.password
            or partes.path != "/voz.xml" or partes.query or partes.fragment):
        raise ValueError("Para editar a fala na tela, TWILIO_TWIML_URL deve apontar para HTTPS do nosso servidor, terminando em /voz.xml.")
    if not re.fullmatch(PADRAO_ID, identificador):
        raise ValueError("Identificador de roteiro inválido.")
    return urlunsplit((partes.scheme, partes.netloc, f"/voz/{identificador}.xml", "", ""))
