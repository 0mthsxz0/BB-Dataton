"""Roteiros imutáveis por chamada, locais e com acesso temporário."""
import json
import os
from pathlib import Path
import re
import secrets
import time
import subprocess
import wave
from urllib.parse import urlsplit, urlunsplit
from xml.etree.ElementTree import Element, SubElement, tostring

from ligacoes import criar_twiml

DURACAO_ROTEIRO = 3600
PADRAO_ID = r"[a-f0-9]{64}"


class RoteiroExpirado(ValueError):
    pass


def pasta_roteiros():
    return Path(os.environ.get("BB_ROTEIROS_DIR") or Path(__file__).parent / "tmp" / "roteiros_voz")


def gerar_audio(mensagem, destino):
    """Sintetiza localmente, sem encaminhar o texto a outro serviço."""
    texto = destino.with_suffix('.txt')
    texto.write_text(mensagem, encoding='utf-8')
    try:
        ambiente = dict(os.environ, BB_AUDIO_TEXTO=str(texto), BB_AUDIO_DESTINO=str(destino))
        script = (Path(__file__).parent / 'scripts' / 'sintetizar_voz.ps1').read_text(encoding='utf-8')
        subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
            env=ambiente, check=True, timeout=15, capture_output=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        with wave.open(str(destino), 'rb') as audio:
            if audio.getnframes() == 0 or audio.getnchannels() != 1 or audio.getframerate() != 16000:
                raise ValueError('Áudio inválido')
    except (OSError, subprocess.SubprocessError, wave.Error, ValueError):
        destino.unlink(missing_ok=True)
        raise ValueError('Não foi possível gerar o áudio local em português. Confira a voz Microsoft Maria Desktop do Windows.') from None
    finally:
        texto.unlink(missing_ok=True)


def salvar_roteiro(mensagem, *, agora=None, audio_base=None):
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
                    arquivo.with_suffix('.wav').unlink(missing_ok=True)
            except FileNotFoundError:
                pass
    identificador = secrets.token_hex(32)
    if audio_base:
        # Valida a URL antes de sintetizar; usa a mesma origem do roteiro.
        endereco = url_roteiro(audio_base, identificador).removesuffix('.xml') + '.wav'
        gerar_audio(mensagem, pasta / f'{identificador}.wav')
        resposta = Element('Response')
        SubElement(resposta, 'Pause', length='1')
        SubElement(resposta, 'Play').text = endereco
        SubElement(resposta, 'Hangup')
        xml = tostring(resposta, encoding='unicode')
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


def ler_audio(identificador):
    ler_roteiro(identificador)  # Aplica a mesma validade e validação do identificador.
    caminho = pasta_roteiros() / f'{identificador}.wav'
    if caminho.is_symlink():
        raise FileNotFoundError('Áudio não encontrado.')
    return caminho.read_bytes()


def url_roteiro(url_base, identificador):
    partes = urlsplit(url_base)
    if (partes.scheme != "https" or not partes.hostname or partes.username or partes.password
            or partes.path != "/voz.xml" or partes.query or partes.fragment):
        raise ValueError("Para editar a fala na tela, TWILIO_TWIML_URL deve apontar para HTTPS do nosso servidor, terminando em /voz.xml.")
    if not re.fullmatch(PADRAO_ID, identificador):
        raise ValueError("Identificador de roteiro inválido.")
    return urlunsplit((partes.scheme, partes.netloc, f"/voz/{identificador}.xml", "", ""))
