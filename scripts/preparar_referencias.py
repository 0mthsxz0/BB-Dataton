"""Prepara referências públicas sem enviar registros de clientes às fontes."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
import subprocess
import time
import unicodedata
from datetime import datetime,timezone
import pandas as pd
import requests
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from referencias import classe_cnae, indicador_climatico, extrair_classes_nr4

NR4 = 'https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/normas-regulamentadora/normas-regulamentadoras-vigentes/nr-04-atualizada-2023.pdf'
RAIZ = Path(__file__).resolve().parents[1]


def texto(v):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(v)).casefold() if not unicodedata.combining(c))


def baixar(url, arquivo):
    if arquivo.exists():
        return arquivo.read_bytes()
    try:
        r = requests.get(url, timeout=90)
    except requests.exceptions.SSLError:
        # Usa a pilha TLS nativa quando há incompatibilidade com OpenSSL, sem desabilitar validação.
        if not url.startswith('https://www.gov.br/'):
            raise
        subprocess.run(['curl','--fail','--location','--max-time','60',
                        '--user-agent','Mozilla/5.0',url,'--output',str(arquivo)],check=True)
        return arquivo.read_bytes()
    if r.status_code == 429:
        raise RuntimeError('Fonte limitou consultas. Execute novamente mais tarde; o cache já obtido será preservado.')
    r.raise_for_status()
    arquivo.write_bytes(r.content)
    return r.content


def json_publico(url, arquivo):
    return json.loads(baixar(url, arquivo))


def preparar_nr4(cache, destino):
    pdf = cache/'nr4_2023.pdf'
    baixar(NR4, pdf)
    linhas = []
    for pagina, p in enumerate(PdfReader(pdf).pages, start=1):
        conteudo = p.extract_text() or ''
        for classe in extrair_classes_nr4(conteudo):
                linhas.append({**classe,'pagina': pagina, 'fonte_nr4': NR4,
                    'versao_nr4': 'PDF atualizado 2023; classificação contextual para o projeto',
                    'sha256_documento': hashlib.sha256(pdf.read_bytes()).hexdigest()})
    df = pd.DataFrame(linhas)
    if len(df) < 300 or df.classe_cnae.duplicated().any():
        raise ValueError('Extração NR-4 incompleta ou ambígua; conferir o documento.')
    df.to_csv(destino/'nr4_cnae.csv',index=False,encoding='utf-8-sig')
    print(f'NR-4: {len(df)} classes extraídas da fonte oficial.',flush=True)


def serie_ibge(cache, tabela, variavel, classificacao=''):
    url = f'https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}/periodos/2021/variaveis/{variavel}?localidades=N6[all]'
    if classificacao:
        url += '&classificacao='+classificacao
    d = json_publico(url,cache/f'ibge_{tabela}_{variavel}.json')
    if len(d) != 1 or len(d[0]['resultados']) != 1:
        raise ValueError('Resposta IBGE com categorias inesperadas.')
    valores = {}
    for s in d[0]['resultados'][0]['series']:
        valor = s['serie'].get('2021')
        try:
            valor = float(valor)
        except (TypeError,ValueError):
            continue
        valores[s['localidade']['id']] = (s['localidade']['nome'],valor)
    return valores


def preparar_seguranca(cache,destino):
    total = serie_ibge(cache,'8508','162')
    furto = serie_ibge(cache,'8510','12456','1353[57310]')
    roubo = serie_ibge(cache,'8512','12462','1351[57304]')
    linhas = []
    for codigo in sorted(total.keys() & furto.keys() & roubo.keys()):
        n = total[codigo][1]
        if n <= 0:
            continue
        f,r = furto[codigo][1]/n,roubo[codigo][1]/n
        if not 0 <= f <= 1 or not 0 <= r <= 1:
            raise ValueError('Taxas de vitimização fora de 0 a 1.')
        linhas.append({'codigo_ibge_municipio':codigo,'municipio':total[codigo][0],
            'taxa_furto_domicilios':f,'taxa_roubo_domicilios':r,'exposicao_bruta':(f+r)/2})
    df = pd.DataFrame(linhas)
    if len(df) < 20:
        raise ValueError('Referência municipal IBGE incompleta.')
    minimo,maximo = df.exposicao_bruta.min(),df.exposicao_bruta.max()
    if maximo <= minimo:
        raise ValueError('Sem dispersão para normalização territorial.')
    df['seguranca_da_cidade_0_1'] = 1-(df.exposicao_bruta-minimo)/(maximo-minimo)
    df['fonte_seguranca'] = 'https://sidra.ibge.gov.br/tabela/8510 | https://sidra.ibge.gov.br/tabela/8512 | https://sidra.ibge.gov.br/tabela/8508'
    df['periodo_seguranca'] = '2021'
    df['granularidade_seguranca'] = 'MUNICIPIO'
    df['confianca_seguranca_0_1'] = .35
    df['metodologia_seguranca'] = f'Média das taxas de domicílios com vítimas; min-max em {len(df)} municípios publicados: {minimo:.12g} a {maximo:.12g}. Proxy domiciliar, não taxa empresarial.'
    df.to_csv(destino/'seguranca_municipal.csv',index=False,encoding='utf-8-sig')
    print(f'IBGE: {len(df)} municípios de referência; dados de 2021.',flush=True)


def preparar_clima(cache,destino,pasta,cfg):
    end = pd.read_csv(pasta/'enderecos_estabelecimentos.csv',dtype=str)
    cidades = end[['codigo_ibge_municipio','municipio_real','uf_real']].drop_duplicates().sort_values('codigo_ibge_municipio')
    resultados = []
    for codigo,nome,uf in cidades.itertuples(index=False,name=None):
        geo_url = 'https://geocoding-api.open-meteo.com/v1/search?'+requests.compat.urlencode({'name':nome,'count':100,'language':'pt','countryCode':'BR','format':'json'})
        geo = json_publico(geo_url,cache/f'geo_{codigo}.json')
        candidatos = [x for x in geo.get('results',[]) if x.get('country_code')=='BR' and texto(x.get('name'))==texto(nome)]
        # Os municípios do pacote são capitais: seleciona o registro de sede administrativa.
        candidatos = [x for x in candidatos if x.get('feature_code') in ('PPLC','PPLA')] or candidatos
        if len(candidatos) != 1:
            raise ValueError(f'Geocodificação ambígua para {nome}/{uf}; conferir coordenada pública.')
        g = candidatos[0]
        estados={'CE':'Ceara','PE':'Pernambuco','BA':'Bahia','MG':'Minas Gerais','RJ':'Rio de Janeiro',
                 'SP':'Sao Paulo','PR':'Parana','RS':'Rio Grande do Sul','GO':'Goias','DF':'Distrito Federal'}
        if uf not in estados or texto(g.get('admin1'))!=texto(estados[uf]):
            raise ValueError(f'Conferir estado da coordenada pública para {nome}/{uf}: {g.get("admin1")}')
        clima_url = 'https://archive-api.open-meteo.com/v1/archive?'+requests.compat.urlencode({
            'latitude':g['latitude'],'longitude':g['longitude'],'start_date':cfg['inicio'],
            'end_date':cfg['fim'],'daily':'wind_gusts_10m_max,precipitation_sum','models':'era5',
            'wind_speed_unit':'kmh','precipitation_unit':'mm','timezone':g.get('timezone','America/Sao_Paulo')})
        arquivo=cache/f'clima_{codigo}_{cfg["inicio"]}_{cfg["fim"]}.json'
        novo=not arquivo.exists()
        d=json_publico(clima_url,arquivo)
        unidades=d['daily_units']
        if unidades.get('wind_gusts_10m_max')!='km/h' or unidades.get('precipitation_sum')!='mm':
            raise ValueError('Unidades climáticas incompatíveis.')
        if d['daily']['time'][0]!=cfg['inicio'] or d['daily']['time'][-1]!=cfg['fim']:
            raise ValueError('Resposta climática não cobre o período solicitado.')
        indicador=indicador_climatico(d['daily'],cfg)
        recente={k:[v for dia,v in zip(d['daily']['time'],vs) if dia>='2016-01-01'] for k,vs in d['daily'].items()}
        alternativo=indicador_climatico(recente,cfg)
        sensivel=dict(cfg,rajada_forte_kmh=40,rajada_severa_kmh=60)
        alt_limiar=indicador_climatico(d['daily'],sensivel)
        resultados.append({'codigo_ibge_municipio':codigo,'municipio':nome,**indicador,
            'exposicao_climatica_2016_2025':alternativo['exposicao_climatica_0_1'],
            'exposicao_climatica_limiares_40_60':alt_limiar['exposicao_climatica_0_1'],
            'fonte_clima':'https://open-meteo.com/en/docs/historical-weather-api',
            'periodo_clima':cfg['inicio']+'/'+cfg['fim'],'granularidade_clima':'MUNICIPIO',
            'confianca_clima_0_1':.55*indicador['completude'],'modelo_clima':'ERA5',
            'latitude_publica':g['latitude'],'longitude_publica':g['longitude'],
            'latitude_celula':d['latitude'],'longitude_celula':d['longitude'],
            'metodologia_clima':json.dumps(cfg,sort_keys=True),
            'sha256_serie':hashlib.sha256(arquivo.read_bytes()).hexdigest()})
        print(f'Clima: {nome}/{uf}; {indicador["dias_vento_validos"]} dias válidos.',flush=True)
        if novo:
            # Uma consulta de 30 anos consome várias unidades da cota pública.
            time.sleep(20)
    pd.DataFrame(resultados).to_csv(destino/'clima_municipal.csv',index=False,encoding='utf-8-sig')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dados',type=Path,required=True)
    p.add_argument('--destino',type=Path,default=RAIZ/'data'/'referencias')
    p.add_argument('--somente',choices=['todos','seguranca','clima','nr4'],default='todos')
    args=p.parse_args()
    args.destino.mkdir(parents=True,exist_ok=True)
    cache=args.destino/'cache';cache.mkdir(exist_ok=True)
    cfg=json.loads((RAIZ/'config_regras.json').read_text(encoding='utf-8-sig'))['clima']
    for nome,funcao in [('nr4',lambda:preparar_nr4(cache,args.destino)),
                        ('seguranca',lambda:preparar_seguranca(cache,args.destino)),
                        ('clima',lambda:preparar_clima(cache,args.destino,args.dados,cfg))]:
        if args.somente in ('todos',nome):
            funcao()
    hashes={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in args.destino.glob('*.csv')}
    manifesto={'gerado_em_utc':datetime.now(timezone.utc).isoformat(),'arquivos':hashes,
        'entradas_cache_sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in cache.iterdir() if x.is_file()},
        'config_clima':cfg}
    (args.destino/'manifesto_fontes.json').write_text(json.dumps(manifesto,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
