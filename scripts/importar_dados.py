"""Copia os CSVs fornecidos, sem versioná-los e sem sobrescrever originais."""
import argparse
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origem', help='Pasta com os nove CSVs do desafio')
    parser.add_argument('--conjunto', choices=['desenvolvimento', 'teste'], default='desenvolvimento')
    args = parser.parse_args()
    origem = Path(args.origem).resolve()
    destino = Path(__file__).resolve().parents[1] / 'data' / args.conjunto
    arquivos = sorted(origem.glob('*.csv'))
    if not (origem / 'dicionario_dados.csv').is_file() or len(arquivos) < 9:
        parser.error('Origem deve conter os nove CSVs, incluindo o dicionário.')
    if destino.exists():
        parser.error(f'Destino já existe; nada foi sobrescrito: {destino}')
    destino.mkdir(parents=True)
    for arquivo in arquivos:
        shutil.copy2(arquivo, destino / arquivo.name)
    print(f'{len(arquivos)} arquivos copiados para {destino}')


if __name__ == '__main__':
    main()
