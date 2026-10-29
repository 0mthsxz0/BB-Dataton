"""Uma chamada HTTP por linha do template; publica CSVs somente após validar todos os casos."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from exportacao import analisar_base, csv_bytes
from templates_api import ENDPOINT, ServicoTemplates, criar_servidor


def consultar(url, token, payload=None):
    request = Request(url, data=None if payload is None else json.dumps(payload).encode(),
                      headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def preencher(url, token, template, destino, comparar=None):
    destino = Path(destino)
    if destino.exists():
        raise ValueError('Pasta de saída já existe. Escolha outra pasta para preservar a entrega anterior.')
    with Path(template).open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    keys = [(r['empresa_id'], r['imovel_id']) for r in rows]
    if not keys or len(keys) != len(set(keys)):
        raise ValueError('Template vazio ou com empresa-estabelecimento duplicado.')
    contrato = consultar(url + '/api/templates/contrato', token)
    if len(keys) != contrato['estabelecimentos']:
        raise ValueError('O template não corresponde ao total de estabelecimentos da API.')
    resultados, coberturas, auditoria, chamadas = [], [], [], []
    inicio = time.perf_counter()
    for i, (empresa, imovel) in enumerate(keys, 1):
        started = time.perf_counter()
        response = consultar(url + ENDPOINT, token, {'empresa_id': empresa, 'imovel_id': imovel})
        if response['metadados'] != contrato:
            raise ValueError('A configuração ou base da API mudou durante o processamento.')
        r, covers = response['resultado'], response['coberturas']
        if (r['empresa_id'], r['imovel_id']) != (empresa, imovel):
            raise ValueError('A API retornou outro estabelecimento.')
        if set(r) != set(contrato['colunas']['template_resultado_times']):
            raise ValueError('Colunas do resultado divergentes do contrato.')
        actual = [c['cobertura'] for c in covers]
        expected = set(r['coberturas_recomendadas'].split('|')) if r['coberturas_recomendadas'] else set()
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError('Coberturas duplicadas ou divergentes da recomendação.')
        if r['elegivel'] == 'NAO' and (covers or r['plano_recomendado']):
            raise ValueError('Caso bloqueado não pode conter oferta.')
        for c in covers:
            if (c['empresa_id'], c['imovel_id']) != (empresa, imovel):
                raise ValueError('Cobertura vinculada a outro estabelecimento.')
            if set(c) != set(contrato['colunas']['template_coberturas_times']):
                raise ValueError('Colunas de cobertura divergentes do contrato.')
            lo, hi = c['faixa_valor_min'], c['faixa_valor_max']
            if (lo is None) != (hi is None) or lo is not None and not 0 <= lo <= hi:
                raise ValueError('Faixa monetária inválida.')
        resultados.append(r)
        coberturas.extend(covers)
        auditoria.append(response['auditoria'])
        chamadas.append({'empresa_id': empresa, 'imovel_id': imovel, 'status_http': 200,
                         'duracao_ms': round(1000 * (time.perf_counter() - started), 2),
                         'resposta_sha256': hashlib.sha256(json.dumps(response, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()})
        if i % 25 == 0 or i == len(keys):
            print(f'{i}/{len(keys)} chamadas concluídas.', flush=True)
    r = pd.DataFrame(resultados, columns=contrato['colunas']['template_resultado_times'])
    c = pd.DataFrame(coberturas, columns=contrato['colunas']['template_coberturas_times'])
    files = {'template_resultado_times.csv': csv_bytes(r), 'template_coberturas_times.csv': csv_bytes(c)}
    equivalencia = None
    if comparar is not None:
        lote_r, lote_c, _ = analisar_base(comparar.base, comparar.config, data_analise=comparar.data_analise.isoformat())
        # A ordem do template pode ser diferente da ordem do cadastro.
        sort_r = lambda df: df.sort_values(['empresa_id', 'imovel_id']).reset_index(drop=True)
        sort_c = lambda df: df.sort_values(['empresa_id', 'imovel_id', 'cobertura']).reset_index(drop=True)
        pd.testing.assert_frame_equal(sort_r(r), sort_r(lote_r), check_dtype=False, check_exact=True)
        pd.testing.assert_frame_equal(sort_c(c), sort_c(lote_c), check_dtype=False, check_exact=True)
        equivalencia = {'valores_identicos': True,
                        'csvs_identicos_byte_a_byte': files['template_resultado_times.csv'] == csv_bytes(lote_r)
                        and files['template_coberturas_times.csv'] == csv_bytes(lote_c)}
    manifesto = {**contrato, 'modo': 'uma_chamada_http_por_estabelecimento', 'url': url,
                 'chamadas_recomendacao': len(chamadas), 'linhas_cobertura': len(c),
                 'duracao_total_segundos': round(time.perf_counter() - inicio, 3),
                 'template_entrada_sha256': hashlib.sha256(Path(template).read_bytes()).hexdigest(),
                 'comparacao_lote': equivalencia,
                 'saidas_sha256': {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}}
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='templates-api-', dir=destino.parent) as temp:
        stage = Path(temp) / 'pronto'
        stage.mkdir()
        for name, content in files.items():
            (stage / name).write_bytes(content)
        for name, content in [('manifesto_api.json', manifesto), ('auditoria.json', auditoria), ('chamadas_api.json', chamadas)]:
            (stage / name).write_text(json.dumps(content, ensure_ascii=False, allow_nan=False, indent=2), encoding='utf-8')
        stage.rename(destino)
    return manifesto


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', required=True)
    parser.add_argument('--saida', required=True)
    parser.add_argument('--url', help='API local já iniciada; sem esta opção inicia uma API temporária.')
    parser.add_argument('--dados', help='Base completa para a API temporária.')
    parser.add_argument('--config')
    parser.add_argument('--referencias')
    parser.add_argument('--data-analise')
    parser.add_argument('--comparar-lote', action='store_true')
    args = parser.parse_args()
    server = worker = service = None
    try:
        if args.url:
            parsed = urlparse(args.url)
            if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.path not in ('', '/') or parsed.query or parsed.fragment or parsed.username:
                parser.error('Informe uma URL HTTP local, sem caminho ou credenciais.')
            if args.comparar_lote or args.config or args.referencias or args.data_analise or args.dados:
                parser.error('Em --url, base, data e regras são definidas pelo servidor. Comparação de lote requer a API temporária.')
            token = os.environ.get('BB_TEMPLATES_API_TOKEN', '')
            if len(token) < 24:
                parser.error('Defina BB_TEMPLATES_API_TOKEN com pelo menos 24 caracteres.')
            url = args.url.rstrip('/')
        else:
            if not args.dados:
                parser.error('Informe --dados para iniciar a API temporária.')
            service = ServicoTemplates(args.dados, args.config, args.data_analise, args.referencias)
            token = secrets.token_urlsafe(32)
            server = criar_servidor(service, token, 0)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            url = f'http://127.0.0.1:{server.server_port}'
        result = preencher(url, token, args.template, args.saida, service if args.comparar_lote else None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        if server:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)


if __name__ == '__main__':
    main()
