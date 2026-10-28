"""Inspeciona uma cópia local VDE, sem fabricar equivalência com roubo comercial."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from territorio_ssp import _texto


def auditar(arquivo, fonte, baixado_em, notas=None):
    arquivo = Path(arquivo)
    momento = datetime.fromisoformat(baixado_em)
    if momento.tzinfo is None:
        raise ValueError('Data do download exige fuso horário.')
    planilha = pd.ExcelFile(arquivo)
    if len(planilha.sheet_names) != 1:
        raise ValueError('Layout VDE não reconhecido: exige uma única aba anual.')
    colunas = pd.read_excel(planilha, nrows=0).columns.tolist()
    obrigatorias = ['uf', 'municipio', 'evento', 'data_referencia', 'abrangencia']
    if not set(obrigatorias) <= set(colunas):
        raise ValueError('Layout VDE sem as colunas esperadas; exige revisão do adaptador.')
    dados = pd.read_excel(planilha, usecols=obrigatorias)
    datas = pd.to_datetime(dados.data_referencia, errors='raise')
    if datas.isna().any() or datas.dt.year.nunique() != 1:
        raise ValueError('Datas ausentes ou mais de um ano no arquivo VDE.')
    eventos = sorted(str(e) for e in dados.evento.dropna().unique())
    comerciais = [e for e in eventos if _texto(e) in ('ROUBO EM COMERCIO', 'ROUBO A ESTABELECIMENTO COMERCIAL')]
    resultado = {
        'fonte': fonte, 'arquivo_original': arquivo.name,
        'baixado_em': momento.isoformat(), 'sha256_original': hashlib.sha256(arquivo.read_bytes()).hexdigest(),
        'linhas': len(dados), 'colunas': colunas, 'categorias': eventos,
        'periodo_inicio': datas.min().date().isoformat(), 'periodo_fim': datas.max().date().isoformat(),
        'meses_presentes_no_arquivo': sorted(int(m) for m in datas.dt.month.unique()),
        'abrangencias': sorted(str(a) for a in dados.abrangencia.dropna().unique()),
        'categorias_comerciais_compativeis': comerciais,
        'uso_no_indice_empresarial': False,
        'motivo': ('Exige adaptador municipal, validação das definições e denominador compatível antes de uso.' if comerciais else
                   'Nenhuma categoria de roubo em comércio encontrada. Outros crimes não substituem essa medida.'),
        'limites': ['Presença de meses no arquivo não comprova cobertura de cada município e categoria.',
                   'Não soma vítimas, ocorrências, pesos ou abrangências diferentes.',
                   'Não calcula taxa por população para representar risco de estabelecimento.',
                   'Hash detecta alteração em relação à cópia; não certifica a qualidade estatística da fonte.'],
    }
    if notas:
        resultado['notas_metodologicas_sha256'] = hashlib.sha256(Path(notas).read_bytes()).hexdigest()
    return resultado


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--arquivo', required=True)
    p.add_argument('--fonte', required=True)
    p.add_argument('--baixado-em', required=True, help='Data real do download, ISO 8601 com fuso')
    p.add_argument('--notas', help='Cópia HTML local das notas metodológicas')
    p.add_argument('--saida', required=True)
    a = p.parse_args()
    resultado = auditar(a.arquivo, a.fonte, a.baixado_em, a.notas)
    destino = Path(a.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'linhas': resultado['linhas'], 'categorias': len(resultado['categorias']),
                      'uso_no_indice_empresarial': False, 'saida': str(destino)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
