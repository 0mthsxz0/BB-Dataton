"""Referências públicas de segurança no contrato do motor principal.

Não importa empresas, bens, respostas ou avaliações individuais do Datathon.
Não converte Mosler, população, vítimas ou totais estaduais em roubo em comércio.
"""
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import json

import pandas as pd

from .banco import registrar_fonte
from .politica_motor import avaliar_seguranca, verificar_snapshot, POLITICA_SEGURANCA

COLUNAS = ['codigo_ibge_municipio', 'municipio', 'uf', 'seguranca_da_cidade_0_1',
    'fonte_seguranca', 'periodo_seguranca', 'granularidade_seguranca',
    'confianca_seguranca_0_1', 'metodologia_seguranca', 'indicador_disponivel',
    'categoria_seguranca', 'roubo_comercio_total', 'estabelecimentos_referencia',
    'taxa_por_mil_estabelecimentos', 'referencia_taxa_por_mil', 'fonte_denominador',
    'ano_denominador', 'meses_observados_seguranca', 'cobertura_municipal_completa',
    'sha256_arquivos', 'atualizado_em_utc']


def inicializar_motor(con):
    con.execute('''CREATE TABLE IF NOT EXISTS referencias_motor (
        codigo_ibge TEXT NOT NULL, ano INTEGER NOT NULL,
        fonte_id INTEGER NOT NULL REFERENCES fontes(id), dados TEXT NOT NULL,
        PRIMARY KEY(codigo_ibge, ano))''')


def hoje_iso(data_analise=None):
    return date.fromisoformat(data_analise) if isinstance(data_analise, str) else data_analise or date.today()


def oficial(url):
    p = urlsplit(url.strip())
    return p.scheme == 'https' and not p.username and not p.password and (
        p.hostname == 'gov.br' or (p.hostname or '').endswith('.gov.br'))


def validar_linha(r, data_analise):
    r = dict(r)
    # Um marcador de simulação no CSV nunca autoriza contornar o contrato.
    if r.get('tipo_seguranca') or 'SIMULA' in r.get('metodologia_seguranca', '').upper():
        raise ValueError('Simulação não pode ser publicada como referência observada.')
    for campo in ['fonte_seguranca', 'fonte_denominador']:
        if not all(oficial(url) for url in r[campo].split('|')):
            raise ValueError(f'{campo}: exige URLs oficiais .gov.br documentadas.')
    r['integridade_seguranca'] = 'VERIFICADA'
    resultado = avaliar_seguranca(r, data_analise)
    if not resultado['utilizavel']:
        raise ValueError(f"{r.get('codigo_ibge_municipio')}: {resultado['status']}: {resultado['motivos'][0]}")
    return {c: r[c] for c in COLUNAS}


def importar_referencia(con, arquivo, data_analise=None):
    """Importa snapshot público revisado e manifestado; não autentica a fonte remota."""
    arquivo = Path(arquivo)
    if verificar_snapshot(arquivo) != 'VERIFICADA':
        raise ValueError('Referência exige manifesto prévio com SHA-256.')
    dados = pd.read_csv(arquivo, dtype=str, keep_default_na=False, encoding='utf-8-sig')
    if {'empresa_id', 'imovel_id', 'cliente_id', 'bem_id'} & set(dados):
        raise ValueError('CSV: cadastros de clientes não são aceitos no banco de segurança.')
    if not set(COLUNAS) <= set(dados):
        raise ValueError('CSV não atende ao contrato de segurança; cadastros de clientes não são aceitos.')
    if dados.empty or dados.codigo_ibge_municipio.duplicated().any():
        raise ValueError('Snapshot vazio ou com municípios duplicados.')
    linhas = [validar_linha(r, hoje_iso(data_analise)) for r in dados.to_dict('records')]
    inicializar_motor(con)
    fonte = registrar_fonte(con, arquivo, 'snapshot:contrato-motor-principal',
        {'politica': POLITICA_SEGURANCA, 'tipo': 'referencia_publica_revisada'})
    for r in linhas:
        ano = int(r['periodo_seguranca'])
        existente = con.execute('SELECT dados FROM referencias_motor WHERE codigo_ibge=? AND ano=?',
                               (r['codigo_ibge_municipio'], ano)).fetchone()
        serializado = json.dumps(r, ensure_ascii=False, sort_keys=True)
        if existente and existente[0] != serializado:
            raise ValueError('Referência divergente para o mesmo município/ano; revisar antes de substituir.')
        con.execute('INSERT OR IGNORE INTO referencias_motor VALUES(?,?,?,?)',
                    (r['codigo_ibge_municipio'], ano, fonte, serializado))
    return {'importadas': len(linhas), 'fonte_id': fonte}


def consultar_motor(con, codigo=None, data_analise=None):
    hoje = hoje_iso(data_analise)
    if codigo is not None and (len(codigo) != 7 or not codigo.isdigit()):
        raise ValueError('Código IBGE exige sete dígitos.')
    existem = con.execute("SELECT 1 FROM sqlite_master WHERE name='referencias_motor'").fetchone()
    linhas, rejeitadas, codigos = [], [], set()
    if existem:
        for row in con.execute('SELECT codigo_ibge,dados FROM referencias_motor ORDER BY codigo_ibge,ano DESC'):
            if codigo is not None and row['codigo_ibge'] != codigo:
                continue
            r = json.loads(row['dados'])
            try:
                validada = validar_linha(r, hoje)
            except ValueError as exc:
                rejeitadas.append(str(exc))
                continue
            if row['codigo_ibge'] not in codigos:
                linhas.append(validada)
                codigos.add(row['codigo_ibge'])
    return {'politica': POLITICA_SEGURANCA, 'data_analise': hoje.isoformat(),
        'status': 'DISPONIVEL' if linhas else 'PENDENTE_FONTES_COMPATIVEIS',
        'municipios_utilizaveis': len(linhas), 'referencias': linhas, 'rejeitadas': rejeitadas,
        'aviso': 'Sem referência elegível, risco territorial desconhecido. Não usar índice Mosler ou população como substitutos.'}


def exportar_motor(con, saida, data_analise=None):
    """Pacote CSV consumível pela main sem importar o pacote Python de mesmo nome."""
    saida = Path(saida)
    if saida.exists():
        raise ValueError('Destino já existe; use uma pasta nova para preservar o pacote anterior.')
    resultado = consultar_motor(con, data_analise=data_analise)
    saida.mkdir(parents=True)
    (saida/'diagnostico_motor.json').write_text(json.dumps(resultado, ensure_ascii=False, indent=2)+'\n')
    if not resultado['referencias']:
        # Não publicar CSV vazio como se fosse uma base pronta.
        return resultado
    csv = saida/'seguranca_ssp.csv'
    pd.DataFrame(resultado['referencias'], columns=COLUNAS).to_csv(csv, index=False, encoding='utf-8-sig')
    manifesto = {'politica': POLITICA_SEGURANCA, 'arquivos': {
        csv.name: hashlib.sha256(csv.read_bytes()).hexdigest()},
        'criado_em': datetime.now(timezone.utc).isoformat(),
        'fontes': [dict(r) for r in con.execute('SELECT url,sha256,coletado_em FROM fontes ORDER BY id')]}
    (saida/'seguranca_ssp.csv.manifesto.json').write_text(json.dumps(manifesto, ensure_ascii=False, indent=2)+'\n')
    return {**resultado, 'csv': str(csv.resolve())}
