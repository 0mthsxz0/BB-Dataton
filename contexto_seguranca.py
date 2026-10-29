"""Contrato v1 de leitura do banco público. Sem rede ou escrita de clientes.

O contexto criminal, a referência empresarial elegível e Mosler são objetos
separados. Apenas a referência elegível pode substituir o evento de roubo.
"""
from contextlib import contextmanager
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import json
import math
import os
import re
import sqlite3

from seguranca import avaliar_seguranca

FORMATO = 'bb-seguranca-publica'
VERSAO_SCHEMA = 1
MODOS = ('complementar', 'referencia_validada')
REQUERIDAS = {
    'municipios': {'codigo_ibge','municipio','uf','populacao','area_km2','ano_populacao','ano_area','fonte_id'},
    'fontes': {'id','url','sha256','coletado_em'},
    'ocorrencias': {'codigo_ibge','crime','mes','ocorrencias'},
    'ocorrencia_fontes': {'codigo_ibge','crime','mes','fonte_id'},
}
CAMPOS_REFERENCIA = ('seguranca_da_cidade_0_1 fonte_seguranca periodo_seguranca '
    'granularidade_seguranca confianca_seguranca_0_1 metodologia_seguranca '
    'indicador_disponivel categoria_seguranca roubo_comercio_total estabelecimentos_referencia '
    'taxa_por_mil_estabelecimentos referencia_taxa_por_mil fonte_denominador '
    'ano_denominador meses_observados_seguranca cobertura_municipal_completa sha256_arquivos atualizado_em_utc').split()


def _data(valor=None):
    return date.fromisoformat(valor) if isinstance(valor,str) else valor or date.today()


def _assinatura(p):
    s=p.stat()
    return (s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def assinatura_banco():
    """Chave para invalidar também os caches da interface ao trocar dados/modo."""
    caminho=os.environ.get('BB_SEGURANCA_DB','')
    partes=[caminho,os.environ.get('BB_SEGURANCA_MODO','complementar')]
    if caminho:
        for p in (Path(caminho),Path(caminho+'.manifesto.json')):
            try: partes.append(_assinatura(p))
            except OSError: partes.append(None)
    return tuple(partes)


@contextmanager
def _abrir(p):
    con=sqlite3.connect(p.resolve().as_uri()+'?mode=ro&immutable=1',uri=True,timeout=2)
    con.row_factory=sqlite3.Row
    try:
        con.execute('PRAGMA trusted_schema=OFF')
        yield con
    finally: con.close()


def _colunas(con,tabela):
    return {r['name'] for r in con.execute('PRAGMA table_info("'+tabela.replace('"','""')+'")')}


@lru_cache(maxsize=4)
def _validar_arquivo(caminho,assinatura,digest):
    p=Path(caminho)
    with p.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=digest:
            raise ValueError('Integridade do banco divergente do manifesto.')
    with _abrir(p) as con:
        tables={r['name'] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for nome,campos in REQUERIDAS.items():
            if nome not in tables or not campos<=_colunas(con,nome):
                raise ValueError('Schema de segurança incompatível: '+nome)
        for nome in tables:
            if {'empresa_id','cliente_id','imovel_id','bem_id'}&_colunas(con,nome):
                raise ValueError('O banco público não pode conter identificadores de clientes.')
        if con.execute('PRAGMA quick_check').fetchone()[0]!='ok' or con.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('Integridade estrutural do banco inválida.')
    if _assinatura(p)!=assinatura:
        raise ValueError('Banco alterado durante validação.')


def validar_pacote(caminho):
    """Manifesto externo obrigatório. Integridade não certifica autoria da fonte."""
    p=Path(caminho).resolve()
    if not p.is_file():raise ValueError('Banco de segurança não encontrado.')
    for sufixo in ('-wal','-journal'):
        aux=Path(str(p)+sufixo)
        if aux.exists() and aux.stat().st_size:raise ValueError('Publicar backup SQLite consolidado, sem journal/WAL.')
    manifesto=Path(str(p)+'.manifesto.json')
    if not manifesto.is_file() or manifesto.stat().st_size>131072:
        raise ValueError('Manifesto do banco ausente ou inválido.')
    m=json.loads(manifesto.read_text(encoding='utf-8'))
    if (not isinstance(m,dict) or m.get('formato')!=FORMATO or type(m.get('versao_schema')) is not int
            or m['versao_schema']!=VERSAO_SCHEMA or m.get('arquivo')!=p.name
            or not re.fullmatch(r'[0-9a-f]{64}',str(m.get('sha256','')))
            or not isinstance(m.get('versao_dados'),str) or not 1<=len(m['versao_dados'])<=100):
        raise ValueError('Formato/versão do pacote de segurança incompatível.')
    if not isinstance(m.get('gerado_em'),str):raise ValueError('Data de publicação ausente.')
    gerado=datetime.fromisoformat(m['gerado_em'].replace('Z','+00:00'))
    if gerado.tzinfo is None or gerado>datetime.now(timezone.utc):
        raise ValueError('Data de publicação inválida.')
    assinatura=_assinatura(p)
    _validar_arquivo(str(p),assinatura,m['sha256'])
    return m


def _oficial(url):
    p=urlsplit(str(url))
    return p.scheme=='https' and not p.username and not p.password and (p.hostname or '').endswith('.gov.br')


def _fontes(con,ids):
    rows=[]
    for fid in sorted(ids):
        r=con.execute('SELECT id,url,sha256,coletado_em FROM fontes WHERE id=?',(fid,)).fetchone()
        if r:rows.append(dict(r))
    return rows


def consultar_contexto(codigo,uf=None,data_analise=None,caminho=None):
    hoje=_data(data_analise)
    r={'contrato':'contexto-seguranca-1.0','status':'NAO_CONFIGURADO','motivo':'Base pública de segurança ainda não configurada.',
       'codigo_ibge':codigo,'data_analise':hoje.isoformat(),'indicadores':[],'fontes':[],
       'referencia_empresarial':None,'qualidade_referencia':None,'versao_dados':None,
       'aviso':'Contexto municipal, sem probabilidade individual ou precisão de rua.'}
    caminho=caminho if caminho is not None else os.environ.get('BB_SEGURANCA_DB')
    if not caminho:return r
    if not isinstance(codigo,str) or not re.fullmatch(r'\d{7}',codigo):
        return {**r,'status':'LOCALIZACAO_INVALIDA','motivo':'Sem código IBGE municipal válido.'}
    try:
        p=Path(caminho).resolve();m=validar_pacote(p);assinatura=_assinatura(p)
        r.update(versao_dados=m['versao_dados'],sha256_banco=m['sha256'],versao_schema=m['versao_schema'])
        with _abrir(p) as con:
            local=con.execute('SELECT * FROM municipios WHERE codigo_ibge=?',(codigo,)).fetchone()
            if not local:return {**r,'status':'MUNICIPIO_NAO_ENCONTRADO','motivo':'Município não consta no cadastro público importado.'}
            if uf and uf!=local['uf']:
                return {**r,'status':'LOCALIZACAO_INVALIDA','motivo':'UF informada diverge do cadastro municipal.'}
            r['municipio']={k:local[k] for k in ['municipio','uf','populacao','area_km2','ano_populacao','ano_area']}
            # As séries só incluem observações mensais publicadas; raw VDE não vira ocorrência.
            corte=hoje.replace(day=1).isoformat()
            ultimo=con.execute('SELECT max(mes) FROM ocorrencias WHERE codigo_ibge=? AND mes<?',(codigo,corte)).fetchone()[0]
            ids={local['fonte_id']}
            if ultimo:
                fim=date.fromisoformat(ultimo)
                if fim.day!=1:raise ValueError('Competência mensal inválida.')
                idx=fim.year*12+fim.month-1-11;inicio=date(idx//12,idx%12+1,1).isoformat()
                idade=(hoje.year-fim.year)*12+hoje.month-fim.month
                r['periodo']={'inicio':inicio[:7],'fim':ultimo[:7],'meses_desde_fim':idade}
                rows=con.execute('''SELECT crime,count(*) meses,sum(ocorrencias) total,
                    sum(CASE WHEN length(mes)!=10 OR substr(mes,9,2)!='01'
                        OR typeof(ocorrencias)!='integer' OR ocorrencias<0 THEN 1 ELSE 0 END) invalidos
                    FROM ocorrencias WHERE codigo_ibge=? AND mes BETWEEN ? AND ? GROUP BY crime''',(codigo,inicio,ultimo))
                for item in rows:
                    if item['invalidos'] or item['meses']>12:raise ValueError('Série municipal inválida.')
                    fids={x[0] for x in con.execute('''SELECT DISTINCT fonte_id FROM ocorrencia_fontes
                        WHERE codigo_ibge=? AND crime=? AND mes BETWEEN ? AND ?''',(codigo,item['crime'],inicio,ultimo))}
                    ids.update(fids)
                    vinculados=con.execute('''SELECT count(DISTINCT o.mes) FROM ocorrencias o
                        JOIN ocorrencia_fontes f USING(codigo_ibge,crime,mes)
                        WHERE o.codigo_ibge=? AND o.crime=? AND o.mes BETWEEN ? AND ?''',
                        (codigo,item['crime'],inicio,ultimo)).fetchone()[0]
                    completo=item['meses']==12 and vinculados==12 and len(fids)==1
                    pop=local['populacao'];ano=local['ano_populacao']
                    denominador=isinstance(pop,(int,float)) and math.isfinite(pop) and pop>0 and ano==fim.year
                    fontes=_fontes(con,fids)
                    revisavel=bool(fontes) and all(_oficial(f['url']) for f in fontes)
                    r['indicadores'].append({'crime':item['crime'],'unidade':'ocorrencias','granularidade':'MUNICIPIO',
                        'meses_observados':item['meses'],'ocorrencias_periodo_observado':item['total'],
                        'ocorrencias_12m':item['total'] if completo else None,
                        'taxa_por_100mil_habitantes':item['total']/pop*100000 if completo and denominador else None,
                        'status':'DESATUALIZADO' if idade>3 else 'COMPLETO_NA_FONTE' if completo and revisavel else 'PARCIAL',
                        'fontes':fontes})
            tables={x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'referencias_motor' in tables:
                for row in con.execute('SELECT dados FROM referencias_motor WHERE codigo_ibge=? ORDER BY ano DESC',(codigo,)):
                    ref=json.loads(row['dados'])
                    # Categoria, UF e município não podem ser fornecidos por dados do cliente.
                    if (ref.get('codigo_ibge_municipio')!=codigo or ref.get('uf')!=local['uf']
                            or ref.get('tipo_seguranca') or 'SIMULA' in str(ref.get('metodologia_seguranca','')).upper()):continue
                    ref['integridade_seguranca']='VERIFICADA'
                    q=avaliar_seguranca(ref,hoje)
                    if q['utilizavel'] and all(_oficial(u.strip()) for c in ['fonte_seguranca','fonte_denominador'] for u in str(ref.get(c,'')).split('|')):
                        r['referencia_empresarial']={k:ref.get(k) for k in CAMPOS_REFERENCIA}
                        r['qualidade_referencia']=q;break
                    if r['qualidade_referencia'] is None:r['qualidade_referencia']=q
            r['fontes']=_fontes(con,ids)
            r['status']='DISPONIVEL' if r['referencia_empresarial'] else 'PARCIAL' if r['indicadores'] else 'SEM_SERIE_MUNICIPAL'
            r['motivo']='Referência empresarial elegível disponível.' if r['referencia_empresarial'] else 'Sem referência de roubo em comércio elegível; demais indicadores são apenas contexto.'
        if _assinatura(p)!=assinatura:raise ValueError('Banco substituído durante consulta; repetir leitura.')
        return r
    except (OSError,sqlite3.Error,ValueError,TypeError,KeyError,OverflowError):
        # Sem caminhos locais, SQL ou mensagens brutas na resposta pública.
        return {**r,'status':'BASE_INDISPONIVEL','motivo':'Base ausente, corrompida ou incompatível com o contrato. Verifique a instalação.',
                'indicadores':[],'fontes':[],'referencia_empresarial':None,'qualidade_referencia':None}


class IntegracaoSeguranca:
    def __init__(self,caminho=None,modo=None):
        self.caminho=caminho if caminho is not None else os.environ.get('BB_SEGURANCA_DB')
        self.modo=modo or os.environ.get('BB_SEGURANCA_MODO','complementar')
        if self.modo not in MODOS:raise ValueError('Modo de segurança inválido: use complementar ou referencia_validada.')
        self._cache={}

    def preparar(self,registro,data_analise):
        r=dict(registro);codigo=r.get('codigo_ibge_municipio','');uf=r.get('uf_real',r.get('uf'))
        p=Path(self.caminho) if self.caminho else None
        try:sig=(_assinatura(p),_assinatura(Path(str(p)+'.manifesto.json'))) if p else None
        except OSError:sig=None
        chave=(codigo,uf,str(data_analise),sig)
        if chave not in self._cache:
            if len(self._cache)>128:self._cache.clear()
            self._cache[chave]=consultar_contexto(codigo,uf,data_analise,self.caminho)
        ctx=dict(self._cache[chave]);ref=ctx.get('referencia_empresarial')
        aplicada=self.modo=='referencia_validada' and ref is not None
        if aplicada:
            original=dict(r)
            for k in ('tipo_seguranca','taxa_roubo_domicilios','taxa_furto_domicilios','exposicao_bruta'):
                r.pop(k,None)
            r.update(ref,integridade_seguranca='VERIFICADA')
            r['arquivo_seguranca']='seguranca.sqlite'
            r['sha256_snapshot_seguranca']=ctx['sha256_banco']
            if not avaliar_seguranca(r,_data(data_analise))['utilizavel']:
                r=original
                aplicada=False
        # Uma referência CSV válida continua sendo avaliada pela política existente.
        ctx.update(modo=self.modo,aplicada_no_motor=aplicada,
            estrategia_evento='referencia_empresarial_banco_v1' if aplicada else 'referencia_existente_com_politica_seguranca_1_0')
        r['contexto_seguranca']=ctx
        return r


def estado_base(caminho=None):
    caminho=caminho if caminho is not None else os.environ.get('BB_SEGURANCA_DB')
    if not caminho:return {'status':'NAO_CONFIGURADO','motivo':'Banco público ainda não configurado.'}
    try:
        m=validar_pacote(caminho)
        with _abrir(Path(caminho)) as con:
            contagens={t:con.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in REQUERIDAS}
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='vde_registros'").fetchone():
                contagens['vde_registros']=con.execute('SELECT count(*) FROM vde_registros').fetchone()[0]
        return {'status':'INSTALADO','versao_dados':m['versao_dados'],'versao_schema':m['versao_schema'],
                'sha256':m['sha256'],'gerado_em':m['gerado_em'],'contagens':contagens,
                'motivo':'Banco verificado. Disponibilidade de referência elegível depende do município e do período.'}
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error):
        return {'status':'BASE_INDISPONIVEL','motivo':'Banco ausente, corrompido ou incompatível; verificar instalação.'}
