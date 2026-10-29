"""Inicia a API persistente local, com a base e configuração escolhidas."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from templates_api import ServicoTemplates, criar_servidor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dados', required=True)
    parser.add_argument('--config')
    parser.add_argument('--referencias')
    parser.add_argument('--data-analise')
    parser.add_argument('--porta', type=int, default=4180)
    args = parser.parse_args()
    token = os.environ.get('BB_TEMPLATES_API_TOKEN', '')
    if len(token) < 24:
        parser.error('Defina BB_TEMPLATES_API_TOKEN com pelo menos 24 caracteres.')
    service = ServicoTemplates(args.dados, args.config, args.data_analise, args.referencias)
    server = criar_servidor(service, token, args.porta)
    print(f'API de templates: http://127.0.0.1:{server.server_port}; {len(service.indices)} estabelecimentos.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
