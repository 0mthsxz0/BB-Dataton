"""Execução em lote sem abrir a interface: python cli.py --dados PASTA."""
import argparse
import json
from exportacao import exportar
from processamento import carregar_base


def main():
    parser = argparse.ArgumentParser(description='Recomendação de seguros empresariais')
    parser.add_argument('--dados', help='Pasta contendo os nove CSVs originais')
    parser.add_argument('--config', help='Configuração JSON; padrão config_regras.json')
    parser.add_argument('--territorio', help='CSV externo municipal com indicadores documentados')
    parser.add_argument('--saida', default='output', help='Pasta de resultados')
    args = parser.parse_args()
    try:
        base = carregar_base(args.dados, args.territorio)
        r, c = exportar(base, args.config, args.saida)
    except (ValueError, KeyError, OSError) as erro:
        parser.exit(1, f'Erro de processamento: {erro}\n')
    print(json.dumps({'estabelecimentos': len(r), 'coberturas': len(c),
                      'planos': r.plano_recomendado.value_counts().to_dict(),
                      'saida': args.saida}, ensure_ascii=False))


if __name__ == '__main__':
    main()
