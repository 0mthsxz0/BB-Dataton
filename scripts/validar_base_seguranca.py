"""Validação independente do snapshot real e da API local; nenhuma rede externa."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.error import HTTPError
from urllib.request import urlopen

import pandas as pd


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raiz', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--api', default='http://localhost:4175')
    a = p.parse_args()
    raiz = a.raiz/'data/seguranca'
    exportacao = raiz/'exportacao'
    con = sqlite3.connect((raiz/'seguranca.sqlite').as_uri()+'?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    df = pd.read_csv(exportacao/'indice_municipal.csv', dtype={'codigo_ibge': str})
    diagnostico = json.loads((exportacao/'diagnostico.json').read_text(encoding='utf-8'))
    manifesto = json.loads((exportacao/'manifesto.json').read_text(encoding='utf-8'))
    for nome, esperado in manifesto['arquivos_sha256'].items():
        assert hashlib.sha256((exportacao/nome).read_bytes()).hexdigest() == esperado, nome
    assert len(df) == con.execute('SELECT count(*) FROM municipios').fetchone()[0] == 5571
    assert df.codigo_ibge.nunique() == len(df)
    assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not con.execute('PRAGMA foreign_key_check').fetchall()
    assert con.execute('SELECT count(*) FROM vde_registros').fetchone()[0] == 69510
    tem_hierarquia = con.execute('SELECT 1 FROM sqlite_master WHERE name=?', ('hierarquia_execucoes',)).fetchone()
    execucao = con.execute('SELECT diagnostico FROM hierarquia_execucoes ORDER BY id DESC LIMIT 1').fetchone() if tem_hierarquia else None
    hierarquia = json.loads(execucao[0]) if execucao else None
    assert con.execute('SELECT count(*) FROM ocorrencias').fetchone()[0] == (hierarquia['observacoes_publicadas'] if hierarquia else 0)
    if hierarquia:
        arquivos_fontes = raiz/'hierarquia'
        manifesto_fontes = json.loads((arquivos_fontes/'manifesto_hierarquia.json').read_text(encoding='utf-8'))
        for nome, esperado in manifesto_fontes['arquivos_sha256'].items():
            assert hashlib.sha256((arquivos_fontes/nome).read_bytes()).hexdigest() == esperado
        series = pd.read_csv(arquivos_fontes/'series_municipais_selecionadas.csv', dtype={'codigo_ibge':str})
        assert len(series) == hierarquia['observacoes_publicadas']
        assert not series.duplicated(['codigo_ibge','crime','mes']).any()
        assert series.codigo_ibge.str.fullmatch(r'\d{7}').all()
        assert series.ocorrencias.sum() == con.execute('SELECT sum(ocorrencias) FROM ocorrencias').fetchone()[0]
    assert df.indice_roubo_0_100.isna().all()
    assert diagnostico['pesos_critic'] == {} and diagnostico['topo_revisao'] == []
    assert df.completude_0_1.between(0, 1).all()
    assert con.execute('SELECT count(*) FROM estabelecimentos').fetchone()[0] == 2978
    sem_correspondencia = [dict(r) for r in con.execute('''SELECT uf,municipio_original,count(*) linhas
        FROM vde_registros WHERE status='municipio_sem_correspondencia' GROUP BY 1,2''')]
    api = []
    for r in con.execute('''SELECT DISTINCT m.codigo_ibge,m.municipio,m.uf,m.populacao
            FROM estabelecimentos e JOIN municipios m USING(codigo_ibge) ORDER BY m.codigo_ibge'''):
        with urlopen(a.api+'/api/seguranca/'+r['codigo_ibge'], timeout=20) as response:
            v = json.load(response)
            assert response.status == 200
        assert v['municipio'] == r['municipio'] and v['uf'] == r['uf']
        assert v['populacao'] == r['populacao'] and v['ano_populacao'] == 2025
        assert v['indice_roubo_0_100'] is None and v['uso_empresarial_validado'] is False
        series = [h for h in v.get('hierarquia_fontes', []) if h['status'] == 'selecionada']
        for h in series:
            valores = con.execute('SELECT count(*),sum(ocorrencias) FROM ocorrencias WHERE codigo_ibge=? AND crime=?',
                                  (r['codigo_ibge'], h['crime'])).fetchone()
            assert valores[0] == 12 and valores[1] == h['ocorrencias_12m']
        api.append({'codigo_ibge': r['codigo_ibge'], 'municipio': v['municipio'], 'status': 200,
                    'indice': None, 'uso_empresarial_validado': False,
                    'series_disponiveis': [{k: h[k] for k in ['crime','fornecedor','ocorrencias_12m','url','sha256']} for h in series]})
    with urlopen(a.api+'/api/seguranca/municipios?uf=SP&q=Sao%20Paulo', timeout=20) as response:
        assert json.load(response)['municipios'][0]['codigo_ibge'] == '3550308'
    for caminho, esperado in [('/api/seguranca/9999999', 404), ('/api/seguranca/municipios?uf=INVALIDA', 400)]:
        try:
            urlopen(a.api+caminho, timeout=20)
        except HTTPError as exc:
            assert exc.code == esperado
        else:
            raise AssertionError('API não recusou parâmetro inválido')
    resultado = {'status': 'validado_com_indice_indisponivel', 'municipios_csv': len(df),
                 'estabelecimentos': 2978, 'vde_registros': 69510,
                 'pesos_critic': {}, 'ranking': [], 'municipios_sem_correspondencia_vde': sem_correspondencia,
                 'consultas_api': api, 'hashes_exportacao': 'conferidos', 'hierarquia': hierarquia}
    (exportacao/'validacao_real.json').write_text(json.dumps(resultado, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    con.close()


if __name__ == '__main__':
    main()
