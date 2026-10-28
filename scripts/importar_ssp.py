"""Importa planilhas locais ou URLs explícitas SSP e prepara referência municipal."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from territorio_ssp import construir_de_manifesto


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifesto',required=True)
    p.add_argument('--saida',default='data/referencias/seguranca_ssp.csv')
    p.add_argument('--ano')
    p.add_argument('--referencia-taxa',type=float,default=100.)
    p.add_argument('--atualizar',action='store_true',help='Baixar novamente URLs já em cache')
    a = p.parse_args()
    r = construir_de_manifesto(a.manifesto,a.saida,ano_referencia=a.ano,
        referencia_taxa_por_mil=a.referencia_taxa,atualizar=a.atualizar)
    print(f'{len(r)} municípios preparados; {r.indicador_disponivel.eq("SIM").sum()} com indicador disponível. Saída: {a.saida}')


if __name__ == '__main__':
    main()
