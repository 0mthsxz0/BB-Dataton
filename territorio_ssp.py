"""Planilhas SSP -> referência municipal rastreável. Sem rede durante a análise."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import math
import re
import unicodedata

import pandas as pd
import requests

MESES = ('JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ')


def _texto(valor):
    if valor is None or pd.isna(valor):
        return ''
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKD', str(valor).strip().upper()).encode('ascii','ignore').decode())


def _numero(valor):
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, str):
        texto = valor.strip().replace(' ', '')
        # Ponto em valor numérico é decimal; separador de milhar textual é reconhecido explicitamente.
        if ',' in texto:
            texto = texto.replace('.', '').replace(',', '.')
        elif re.fullmatch(r'\d{1,3}(\.\d{3})+', texto):
            texto = texto.replace('.', '')
        valor = texto
    try:
        n = float(valor)
        return n if math.isfinite(n) and n >= 0 else None
    except (ValueError, TypeError):
        return None


def ler_balanco_ssp(caminho, *, uf, regiao, ano, codigo_ibge_municipio,
                    fonte, estabelecimentos=None, cobertura_municipal_completa='NAO'):
    caminho = Path(caminho)
    raw = pd.read_excel(caminho, header=None)
    cabecalho = None
    for i in range(len(raw)):
        valores = [_texto(v) for v in raw.iloc[i]]
        if any('NATUREZA DO CRIME' in v for v in valores) and 'TOTAL' in valores:
            cabecalho = (i, next(j for j,v in enumerate(valores) if 'NATUREZA DO CRIME' in v),
                         valores.index('TOTAL'), {v:j for j,v in enumerate(valores) if v in MESES})
            break
    if cabecalho is None:
        raise ValueError('Planilha SSP sem cabeçalho reconhecido de natureza e total.')
    inicio, coluna, total_col, meses_col = cabecalho
    encontrados = [i for i in range(inicio+1,len(raw))
                   if _texto(raw.iat[i,coluna]) == 'ROUBO EM COMERCIO']
    if len(encontrados) != 1:
        raise ValueError('A planilha deve conter uma única linha exata de Roubo em Comércio.')
    i = encontrados[0]
    meses = [_numero(raw.iat[i,meses_col[m]]) if m in meses_col else None for m in MESES]
    total = _numero(raw.iat[i,total_col])
    completos = all(x is not None for x in meses)
    if completos:
        soma = sum(meses)
        if total is not None and not math.isclose(total,soma,abs_tol=1e-6):
            raise ValueError('Total SSP diverge da soma dos doze meses.')
        total = soma
    else:
        # Um total não comprova que o ano esteja completo; não anualiza meses faltantes.
        total = None
    if any(x is not None and not x.is_integer() for x in meses):
        raise ValueError('Contagens de ocorrências SSP devem ser inteiras.')
    return {'uf':uf, 'regiao_administrativa':regiao, 'ano':str(ano),
        'codigo_ibge_municipio':str(codigo_ibge_municipio), 'roubo_comercio_total':total,
        'meses_observados':sum(x is not None for x in meses), 'estabelecimentos':_numero(estabelecimentos),
        'cobertura_municipal_completa':cobertura_municipal_completa, 'fonte':fonte,
        'sha256_arquivo':hashlib.sha256(caminho.read_bytes()).hexdigest()}


def construir_enriquecimento(registros, *, ano_referencia=None, referencia_taxa_por_mil=100.):
    """Taxa = soma das ocorrências / soma dos estabelecimentos; um único ano comparável.

    R = taxa/(taxa+referência fixa). A referência é uma hipótese configurável,
    não ajustada ao conjunto consultado e não representa uma probabilidade.
    """
    referencia = _numero(referencia_taxa_por_mil)
    if referencia is None or referencia <= 0:
        raise ValueError('Referência SSP por mil deve ser positiva.')
    registros = [dict(r) for r in registros]
    if not registros:
        raise ValueError('Manifesto SSP vazio.')
    anos = {str(r.get('ano','')) for r in registros}
    if any(not re.fullmatch(r'[0-9]{4}',a) for a in anos):
        raise ValueError('Ano SSP deve ter quatro dígitos.')
    if ano_referencia is None and len(anos) != 1:
        raise ValueError('Selecione um único ano SSP; não misture períodos.')
    ano = str(ano_referencia) if ano_referencia is not None else next(iter(anos))
    registros = [r for r in registros if str(r['ano']) == ano]
    if not registros:
        raise ValueError('Ano SSP selecionado sem registros.')
    grupos = {}
    chaves = set()
    for r in registros:
        ibge = str(r.get('codigo_ibge_municipio',''))
        if not re.fullmatch(r'[0-9]{7}',ibge) or not re.fullmatch('[A-Z]{2}',str(r.get('uf',''))):
            raise ValueError('Registro SSP sem código IBGE ou UF válido.')
        regiao = _texto(r.get('regiao_administrativa'))
        if not regiao or not r.get('fonte') or not r.get('sha256_arquivo'):
            raise ValueError('SSP exige região, fonte e hash do arquivo.')
        chave = (ibge,regiao)
        if chave in chaves:
            raise ValueError('Região SSP duplicada no mesmo município e ano.')
        chaves.add(chave)
        grupos.setdefault(ibge,[]).append(r)
    saida = []
    for ibge, linhas in sorted(grupos.items()):
        if len({r['uf'] for r in linhas}) != 1:
            raise ValueError('UFs divergentes no mesmo município SSP.')
        if any(str(r.get('cobertura_municipal_completa','')).upper() != 'SIM' for r in linhas):
            raise ValueError('Confirme cobertura municipal completa, sem sobreposição entre regiões.')
        regioes = {_texto(r['regiao_administrativa']) for r in linhas}
        if len(linhas)>1 and regioes & {'TOTAL','MUNICIPIO','DISTRITO FEDERAL','BRASILIA'}:
            raise ValueError('Não misture total municipal e regiões; isso duplica ocorrências.')
        totais = [_numero(r.get('roubo_comercio_total')) for r in linhas]
        denominadores = [_numero(r.get('estabelecimentos')) for r in linhas]
        completo = all(r.get('meses_observados') == 12 for r in linhas) and all(x is not None for x in totais)
        denominador_ok = all(x is not None and x > 0 and x.is_integer() for x in denominadores)
        if any(x is not None and not x.is_integer() for x in totais):
            raise ValueError('Ocorrências SSP devem ser contagens inteiras.')
        total = sum(totais) if completo else None
        estabelecimentos = sum(denominadores) if denominador_ok else None
        taxa = total/estabelecimentos*1000 if completo and denominador_ok else None
        risco = taxa/(taxa+referencia) if taxa is not None else None
        observacao = ('Taxa anual por mil estabelecimentos; ocorrências não são empresas distintas.' if taxa is not None
                      else 'INDISPONÍVEL: período incompleto, contagem ausente ou sem denominador de estabelecimentos; ponto central 0,5 com confiança zero.')
        saida.append({'codigo_ibge_municipio':ibge,'uf':linhas[0]['uf'],
            'seguranca_da_cidade_0_1':1-risco if risco is not None else .5,
            'confianca_seguranca_0_1':.55 if risco is not None else 0.,
            'fonte_seguranca':' | '.join(sorted({r['fonte'] for r in linhas})),
            'periodo_seguranca':ano,'granularidade_seguranca':'MUNICIPIO',
            'metodologia_seguranca':f'SSP Roubo em Comércio. R=t/(t+{referencia:g}); t=soma(ocorrências)/soma(estabelecimentos)*1000. Hipótese fixa. '+observacao,
            'indicador_disponivel':'SIM' if taxa is not None else 'NAO',
            'roubo_comercio_total':total,'estabelecimentos_referencia':estabelecimentos,
            'taxa_por_mil_estabelecimentos':taxa,'referencia_taxa_por_mil':referencia,
            'regioes_fonte':'|'.join(sorted(regioes)),
            'sha256_arquivos':'|'.join(sorted({r['sha256_arquivo'] for r in linhas})),
            'atualizado_em_utc':datetime.now(timezone.utc).isoformat()})
    return pd.DataFrame(saida)


def construir_de_manifesto(manifesto_csv, destino, *, ano_referencia=None,
                          referencia_taxa_por_mil=100., atualizar=False):
    """Arquivos locais ou URLs explícitas; cache por URL. Atualização é deliberada."""
    manifesto = pd.read_csv(manifesto_csv,dtype=str,keep_default_na=False)
    raiz = Path(manifesto_csv).resolve().parent
    registros = []
    for linha in manifesto.to_dict('records'):
        url = linha.get('url','')
        if url:
            if not url.startswith('https://'):
                raise ValueError('Downloads SSP exigem URL HTTPS.')
            cache = raiz/'cache_ssp'
            cache.mkdir(exist_ok=True)
            extensao = '.xls' if linha.get('formato') == 'xls' else '.xlsx'
            caminho = cache/(hashlib.sha256(url.encode()).hexdigest()+extensao)
            if atualizar or not caminho.exists():
                resposta = requests.get(url,timeout=(5,60))
                resposta.raise_for_status()
                conteudo = resposta.content
                if not (conteudo.startswith(b'PK') or conteudo.startswith(bytes.fromhex('D0CF11E0A1B11AE1'))):
                    raise ValueError('Download SSP não retornou uma planilha XLS/XLSX.')
                caminho.write_bytes(conteudo)
        else:
            if not linha.get('arquivo'):
                raise ValueError('Manifesto exige arquivo local ou URL de planilha.')
            caminho = Path(linha['arquivo'])
            if not caminho.is_absolute():
                caminho = raiz/caminho
        registros.append(ler_balanco_ssp(caminho,uf=linha['uf'],regiao=linha['regiao'],ano=linha['ano'],
            codigo_ibge_municipio=linha['codigo_ibge_municipio'],fonte=linha.get('fonte') or url,
            estabelecimentos=linha.get('estabelecimentos'),
            cobertura_municipal_completa=linha.get('cobertura_municipal_completa','NAO')))
    resultado = construir_enriquecimento(registros,ano_referencia=ano_referencia,referencia_taxa_por_mil=referencia_taxa_por_mil)
    destino = Path(destino)
    destino.parent.mkdir(parents=True,exist_ok=True)
    resultado.to_csv(destino,index=False,encoding='utf-8-sig')
    return resultado
