"""JSON por stdin/stdout. O servidor Node limita corpo, tempo e concorrência."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cotacao_service import analisar, analisar_cadastro, analisar_cnae, contexto, consultar_perfil_cnae, consultar_atividade_cnae


def main():
    try:
        request = json.load(sys.stdin)
        if request.get('action') == 'contexto':
            result = contexto()
        elif request.get('action') == 'perfil_cnae':
            result = consultar_perfil_cnae(request.get('payload'))
        elif request.get('action') == 'cadastro':
            result = analisar_cadastro(request.get('payload'))
        elif request.get('action') == 'relatorio_cnae':
            result = analisar_cnae(request.get('payload'))
        else:
            result = analisar(request.get('payload'))
        print(json.dumps({'ok': True, 'data': result}, ensure_ascii=True, allow_nan=False))
    except ValueError as error:
        print(json.dumps({'ok': False, 'status': 422, 'error': str(error)}, ensure_ascii=True))
    except Exception:
        # No local paths, private records or tracebacks in an HTTP response.
        print(json.dumps({'ok': False, 'status': 503, 'error': 'Motor indisponível. Confira Python, dependências e os CSVs no servidor.'}))


if __name__ == '__main__':
    main()
