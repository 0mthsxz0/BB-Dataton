"""Prepara somente fontes públicas e diagnostica prontidão para o motor da main.

Não importa arquivos do Datathon. Falhas de rede ou falta de referência comercial
produzem saída 2 e um relatório, nunca uma base artificialmente completa.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seguranca.banco import conectar, inicializar, importar_ibge, importar_populacao
from seguranca.fontes import download, LOCALIDADES, INDICADORES
from seguranca.motor_principal import importar_referencia, exportar_motor
from seguranca.vde import importar_vde

RAIZ = Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--banco',type=Path,default=RAIZ/'data/seguranca/seguranca.sqlite')
    p.add_argument('--fontes',type=Path,default=RAIZ/'data/seguranca/fontes')
    p.add_argument('--saida',type=Path,required=True,help='Pasta nova do pacote e diagnóstico')
    p.add_argument('--referencia-motor',type=Path,help='Snapshot público revisado + manifesto, no contrato da main')
    p.add_argument('--sem-rede',action='store_true',help='Usa apenas arquivos já capturados com metadados válidos')
    a=p.parse_args()
    if a.saida.exists():p.error('Use uma pasta de saída nova; nada será sobrescrito.')
    fontes={
      'ibge/localidades.json':LOCALIDADES,
      'ibge/indicadores.json':INDICADORES,
      'ibge/populacao_2025.json':'https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/2025/variaveis/9324?localidades=N6[all]',
      'sinesp/bancovde-2025.xlsx':'https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/download/dnsp-base-de-dados/bancovde-2025.xlsx/@@download/file'}
    def coletar(item):
        nome,url=item;arquivo=a.fontes/nome
        try:
            if a.sem_rede and not (arquivo.exists() and arquivo.with_name(arquivo.name+'.fonte.json').exists()):
                raise ValueError('Arquivo não disponível no cache; rede desativada.')
            return nome,{'status':'disponivel',**download(url,arquivo)}
        except Exception as e:
            return nome,{'status':'pendente','url':url,'erro':str(e)}
    with ThreadPoolExecutor(max_workers=4) as executor:
        coleta=dict(executor.map(coletar,fontes.items()))
    etapas={}
    with conectar(a.banco) as con:
        inicializar(con)
        if all(coleta[k]['status']=='disponivel' for k in ['ibge/localidades.json','ibge/indicadores.json']):
            etapas['ibge']=importar_ibge(con,a.fontes/'ibge/localidades.json',a.fontes/'ibge/indicadores.json',LOCALIDADES,INDICADORES)
        if coleta['ibge/populacao_2025.json']['status']=='disponivel' and con.execute('SELECT count(*) FROM municipios').fetchone()[0]:
            etapas['populacao']=importar_populacao(con,a.fontes/'ibge/populacao_2025.json',fontes['ibge/populacao_2025.json'],2025)
        vde='sinesp/bancovde-2025.xlsx'
        if coleta[vde]['status']=='disponivel':
            digest=coleta[vde]['sha256']
            tem_tabela=con.execute("SELECT 1 FROM sqlite_master WHERE name='vde_registros'").fetchone()
            atual=con.execute('SELECT 1 FROM vde_registros v JOIN fontes f ON f.id=v.fonte_id WHERE f.sha256=? LIMIT 1',(digest,)).fetchone() if tem_tabela else None
            if atual:
                etapas['sinesp']='Snapshot já importado; preservado. Reimportação municipal exige comando explícito após atualização do cadastro.'
            else:
                bruto=not con.execute('SELECT 1 FROM municipios LIMIT 1').fetchone()
                etapas['sinesp']=importar_vde(con,a.fontes/vde,fontes[vde],somente_bruto=bruto)
        if a.referencia_motor:
            etapas['referencia_motor']=importar_referencia(con,a.referencia_motor)
    with conectar(a.banco,somente_leitura=True) as con:
        r=exportar_motor(con,a.saida)
        contagens={t:con.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ['municipios','ocorrencias','fontes']}
        tabelas={x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'vde_registros' in tabelas:
            contagens['vde_registros']=con.execute('SELECT count(*) FROM vde_registros').fetchone()[0]
        integridade=con.execute('PRAGMA integrity_check').fetchone()[0]
        fk=list(con.execute('PRAGMA foreign_key_check'))
        clientes=[t for t in ['empresas','estabelecimentos','bens_cadastrados'] if t in tabelas]
    resultado={'criado_em':datetime.now(timezone.utc).isoformat(),'status_motor':r['status'],
      'municipios_utilizaveis':r['municipios_utilizaveis'],'coleta':coleta,'etapas':etapas,
      'contagens':contagens,'integridade_sqlite':integridade,'violacoes_fk':len(fk),
      'tabelas_clientes_encontradas':clientes,'banco':str(a.banco.resolve())}
    (a.saida/'preparacao.json').write_text(json.dumps(resultado,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(resultado,ensure_ascii=False,indent=2))
    return 0 if r['municipios_utilizaveis'] and integridade=='ok' and not fk and not clientes else 2


if __name__=='__main__':
    sys.exit(main())
