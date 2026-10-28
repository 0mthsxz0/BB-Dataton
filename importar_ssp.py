"""Gera enriquecimento territorial a partir de um manifesto de arquivos SSP."""
import argparse

from territorio_ssp import construir_de_manifesto


def main():
    parser = argparse.ArgumentParser(description="Importar balanços criminais de SSPs")
    parser.add_argument("--manifesto", required=True, help="CSV com arquivo, uf, regiao, ano e codigo_ibge_municipio")
    parser.add_argument("--saida", default="territorio_ssp.csv")
    args = parser.parse_args()
    resultado = construir_de_manifesto(args.manifesto, args.saida)
    print(f"{len(resultado)} municípios exportados para {args.saida}")


if __name__ == "__main__":
    main()
