"""Coleta de arquivos oficiais com TLS, cache, hashes e inventário de links."""
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote
import hashlib
import json
import os
import re

import requests

from .banco import normalizar


SINESP = 'https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica'
LOCALIDADES = 'https://servicodados.ibge.gov.br/api/v1/localidades/municipios'
INDICADORES = 'https://servicodados.ibge.gov.br/api/v3/agregados/4714/periodos/2022/variaveis/93%7C6318?localidades=N6[all]'
EXTENSOES = {'.csv', '.xlsx', '.xls', '.zip', '.pdf', '.ods', '.doc', '.docx'}


def oficial(url):
    p = urlsplit(url)
    return (p.scheme == 'https' and p.username is None and p.password is None
            and (p.hostname in {'www.gov.br', 'gov.br', 'dados.gov.br'}
                 or (p.hostname or '').endswith('.mj.gov.br')
                 or (p.hostname or '').endswith('.ibge.gov.br')))


def download(url, arquivo, atualizar=False, limite_mb=250):
    if not oficial(url):
        raise ValueError(f'Fonte precisa ser HTTPS em domínio oficial MJ/IBGE/gov.br: {url}')
    arquivo = Path(arquivo)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    meta = arquivo.with_name(arquivo.name+'.fonte.json')
    if arquivo.exists() and meta.exists() and not atualizar:
        d = json.loads(meta.read_text(encoding='utf-8'))
        with arquivo.open('rb') as f:
            digest = hashlib.file_digest(f, 'sha256').hexdigest()
        if d.get('url') != url or digest != d['sha256']:
            raise ValueError(f'Cache divergente: {arquivo}; não reutilizar sem verificar a origem.')
        return d
    if arquivo.exists() and not meta.exists():
        raise ValueError(f'Arquivo sem metadados já existe: {arquivo}; não sobrescrever.')
    parcial = arquivo.with_name(arquivo.name+'.partial')
    try:
        # Redirecionamentos são seguidos explicitamente para manter a restrição de origem.
        destino = url
        for _ in range(6):
            resposta = requests.get(destino, stream=True, timeout=(15, 90), allow_redirects=False,
                                    headers={'User-Agent': 'BB-Dataton-pesquisa-dados-publicos/1.0'})
            if resposta.is_redirect:
                proximo = urljoin(destino, resposta.headers['Location'])
                resposta.close()
                if not oficial(proximo):
                    raise ValueError(f'Redirecionamento para domínio não autorizado: {proximo}')
                destino = proximo
                continue
            break
        else:
            raise ValueError('Redirecionamentos demais na fonte oficial.')
        with resposta:
            resposta.raise_for_status()
            digest, tamanho = hashlib.sha256(), 0
            with parcial.open('wb') as f:
                for bloco in resposta.iter_content(1024*1024):
                    tamanho += len(bloco)
                    if tamanho > limite_mb*1024*1024:
                        raise ValueError(f'Arquivo excede limite explícito de {limite_mb} MB; revisar antes de baixar.')
                    digest.update(bloco)
                    f.write(bloco)
            tipo = resposta.headers.get('Content-Type', '')
            if arquivo.suffix.lower() in EXTENSOES and ('text/html' in tipo or 'application/json' in tipo):
                raise ValueError('Download devolveu página/erro em lugar do arquivo de dados.')
            d = {'url': url, 'url_final': destino, 'arquivo': str(arquivo.resolve()), 'bytes': tamanho,
                 'sha256': digest.hexdigest(), 'content_type': tipo,
                 'coletado_em': datetime.now(timezone.utc).isoformat()}
            os.replace(parcial, arquivo)
            meta.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            return d
    finally:
        parcial.unlink(missing_ok=True)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.atual = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.atual = {'href': dict(attrs).get('href', ''), 'texto': ''}

    def handle_data(self, data):
        if self.atual is not None:
            self.atual['texto'] += data

    def handle_endtag(self, tag):
        if tag == 'a' and self.atual:
            self.links.append(self.atual)
            self.atual = None


def coletar_sinesp(destino, pagina=SINESP, atualizar=False, limite_paginas=40):
    """Inventaria portal estatístico e baixa documentos vinculados a municípios.

    A descoberta é conservadora e auditável. Não promete esgotar arquivos que
    dependem de Power BI, autenticação, JavaScript ou links não publicados.
    """
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    fila, vistos, arquivos, falhas = [(pagina, 0, False)], set(), {}, []
    paginas = []
    while fila and len(vistos) < limite_paginas:
        url, nivel, municipal = fila.pop(0)
        if url in vistos:
            continue
        vistos.add(url)
        nome = hashlib.sha256(url.encode()).hexdigest()[:16]+'.html'
        try:
            meta = download(url, destino/'paginas'/nome, atualizar)
            html = Path(meta['arquivo']).read_text(encoding='utf-8', errors='replace')
            parser = Links()
            parser.feed(html)
            paginas.append(meta)
            for link in parser.links:
                absoluto = urljoin(url, link['href']).split('#')[0]
                if not oficial(absoluto):
                    continue
                caminho = urlsplit(absoluto).path
                texto = normalizar(unquote(caminho)+' '+link['texto'])
                eh_municipal = municipal or 'municip' in texto
                ext = Path(caminho.removesuffix('/@@download/file')).suffix.lower()
                if ext in EXTENSOES:
                    anterior = arquivos.get(absoluto, {})
                    arquivos[absoluto] = {'url': absoluto, 'titulo': link['texto'].strip(),
                                          'municipal_no_link': eh_municipal or anterior.get('municipal_no_link', False)}
                elif nivel < 3 and ('/estatistica' in caminho or '/dados-nacionais' in caminho):
                    if absoluto not in vistos:
                        fila.append((absoluto, nivel+1, eh_municipal))
        except (requests.RequestException, ValueError, OSError) as exc:
            falhas.append({'url': url, 'erro': str(exc)[:500]})
    baixados = []
    for item in arquivos.values():
        if not item['municipal_no_link']:
            continue
        url = item['url']
        nome = Path(unquote(urlsplit(url).path.removesuffix('/@@download/file'))).name
        nome = re.sub(r'[^A-Za-z0-9._-]', '_', nome)
        nome = hashlib.sha256(url.encode()).hexdigest()[:12]+'_'+nome
        try:
            baixados.append({**item, **download(url, destino/'documentos'/nome, atualizar)})
        except (requests.RequestException, ValueError, OSError) as exc:
            falhas.append({'url': url, 'erro': str(exc)[:500]})
    inventario = {'pagina_inicial': pagina, 'coletado_em': datetime.now(timezone.utc).isoformat(),
                  'paginas': paginas, 'links_documentos': list(arquivos.values()), 'baixados': baixados,
                  'falhas': falhas, 'limite_paginas_atingido': bool(fila),
                  'escopo': 'Documentos com indicação municipal nos links do portal estatístico; revisar inventário antes de importar.'}
    (destino/'inventario_sinesp.json').write_text(json.dumps(inventario, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return inventario


def coletar_ibge(destino, atualizar=False):
    destino = Path(destino)
    return [download(LOCALIDADES, destino/'ibge_municipios.json', atualizar),
            download(INDICADORES, destino/'ibge_censo_2022.json', atualizar)]
