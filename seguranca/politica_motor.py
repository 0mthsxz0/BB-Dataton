# Contrato copiado da main b8c86080d97ebd493c503a02fac5b6130c741fff.
"""Contrato de uso da referência territorial. Ausência nunca significa segurança.

Elegibilidade dos dados não é calibração atuarial nem probabilidade de sinistro.
"""
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re

POLITICA_SEGURANCA = 'seguranca-1.0'
MAX_MESES_DEFASAGEM = 24  # Regra editorial de validade, não estimativa estatística.
UF_PREFIXOS = dict(zip('RO AC AM RR PA AP TO MA PI CE RN PB PE AL SE BA MG ES RJ SP PR SC RS MS MT GO DF'.split(),
                      '11 12 13 14 15 16 17 21 22 23 24 25 26 27 28 29 31 32 33 35 41 42 43 50 51 52 53'.split()))


def _numero(v):
    if isinstance(v, bool):
        return None
    try:
        n = float(v)
        return n if math.isfinite(n) and n >= 0 else None
    except (ValueError, TypeError):
        return None


def avaliar_seguranca(r, data_analise=None):
    hoje = data_analise or date.today()
    if isinstance(hoje, str):
        hoje = date.fromisoformat(hoje)
    resultado = {'politica': POLITICA_SEGURANCA, 'data_analise': hoje.isoformat(),
                 'max_meses_defasagem': MAX_MESES_DEFASAGEM, 'utilizavel': False,
                 'calibrado': False, 'status': 'INDISPONIVEL', 'motivos': []}

    def rejeitar(status, motivo):
        resultado.update(status=status, motivos=[motivo])
        return resultado

    n = _numero(r.get('seguranca_da_cidade_0_1'))
    confianca = _numero(r.get('confianca_seguranca_0_1', r.get('confianca_territorial_0_1')))
    if n is None or n > 1 or confianca is None or not 0 < confianca <= 1 or r.get('indicador_disponivel') == 'NAO':
        return rejeitar('INDISPONIVEL', 'Referência ausente ou sem confiança utilizável; risco territorial desconhecido.')
    if r.get('tipo_seguranca') == 'SIMULACAO':
        resultado.update(utilizavel=True, status='SIMULACAO', motivos=['Cenário hipotético; não é criminalidade observada.'])
        return resultado
    codigo = str(r.get('codigo_ibge_municipio') or '')
    uf = str(r.get('uf_real', r.get('uf')) or '')
    if not re.fullmatch(r'[0-9]{7}', codigo) or not codigo.startswith(UF_PREFIXOS.get(uf, '!')):
        return rejeitar('LOCALIZACAO_INVALIDA', 'Código IBGE municipal ausente ou incompatível com a UF; vínculo territorial rejeitado.')
    metodologia = str(r.get('metodologia_seguranca') or '')
    if ('domicil' in metodologia.lower() or any(_numero(r.get(k)) is not None for k in
            ('taxa_furto_domicilios', 'taxa_roubo_domicilios'))):
        return rejeitar('INCOMPATIVEL', 'Vitimização domiciliar não mede roubo a comércio; referência excluída do índice empresarial.')
    periodo = str(r.get('periodo_seguranca', r.get('ano_referencia')) or '')
    if not re.fullmatch(r'[0-9]{4}', periodo) or not 1900 <= int(periodo) < hoje.year:
        return rejeitar('PERIODO_INVALIDO', 'Exige ano civil encerrado; dados parciais ou futuros não são anualizados.')
    meses = (hoje.year - int(periodo)) * 12 + hoje.month - 12
    resultado['meses_desde_fim_periodo'] = meses
    if meses > MAX_MESES_DEFASAGEM:
        return rejeitar('DESATUALIZADO', 'Base fora da validade de 24 meses após o ano observado; atualizar o snapshot.')
    if r.get('integridade_seguranca') != 'VERIFICADA':
        return rejeitar('INTEGRIDADE_NAO_VERIFICADA', 'Sem manifesto com hash previamente registrado; referência não utilizada.')
    obrigatorios = ('fonte_seguranca', 'metodologia_seguranca', 'fonte_denominador', 'sha256_arquivos')
    if any(not str(r.get(k) or '').strip() for k in obrigatorios):
        return rejeitar('METADADOS_INSUFICIENTES', 'Faltam fonte, metodologia, origem do denominador ou hashes dos originais.')
    if r.get('categoria_seguranca') != 'ROUBO_EM_COMERCIO':
        return rejeitar('INCOMPATIVEL', 'Categoria criminal incompatível com roubo em comércio; não substituir por outros crimes.')
    if (str(r.get('ano_denominador')) != periodo or
            _numero(r.get('meses_observados_seguranca')) != 12 or
            r.get('cobertura_municipal_completa') != 'SIM' or
            r.get('granularidade_seguranca') != 'MUNICIPIO'):
        return rejeitar('COBERTURA_INSUFICIENTE', 'Exige doze meses, cobertura municipal completa e estabelecimentos do mesmo ano.')
    total, denominador, taxa, referencia = [_numero(r.get(k)) for k in
        ('roubo_comercio_total', 'estabelecimentos_referencia', 'taxa_por_mil_estabelecimentos', 'referencia_taxa_por_mil')]
    if (any(v is None for v in (total, denominador, taxa, referencia)) or denominador <= 0 or referencia <= 0
            or not total.is_integer() or not denominador.is_integer()
            or not math.isclose(taxa, total / denominador * 1000, rel_tol=1e-8, abs_tol=1e-8)
            or not math.isclose(n, referencia / (taxa + referencia), rel_tol=1e-8, abs_tol=1e-8)):
        return rejeitar('INCONSISTENTE', 'Contagem, denominador, taxa ou transformação territorial inconsistentes.')
    if not all(re.fullmatch(r'[0-9a-f]{64}', h) for h in str(r['sha256_arquivos']).split('|')):
        return rejeitar('INCONSISTENTE', 'Hash dos originais inválido.')
    resultado.update(utilizavel=True, status='EXPERIMENTAL', motivos=[
        'Referência de roubo em comércio elegível; escala experimental sem calibração por sinistros. Não mede furto nem risco de rua.'])
    return resultado


def verificar_snapshot(caminho, conteudo=None):
    """Confere hashes previamente congelados; não autentica o conteúdo da fonte."""
    caminho = Path(caminho)
    manifesto = caminho.with_name(caminho.name + '.manifesto.json')
    if not manifesto.exists():
        manifesto = caminho.parent / 'manifesto_fontes.json'
    if not manifesto.exists():
        return 'SEM_MANIFESTO'
    dados = json.loads(manifesto.read_text(encoding='utf-8-sig'))
    if not isinstance(dados, dict) or not isinstance(dados.get('arquivos'), dict):
        raise ValueError('Manifesto de segurança sem mapa de arquivos e hashes.')
    esperado = dados.get('arquivos', {}).get(caminho.name)
    bruto = caminho.read_bytes() if conteudo is None else conteudo
    hashes = {hashlib.sha256(bruto).hexdigest()}
    # Os snapshots CSV/JSON foram preparados no Windows com CRLF, mas o Git
    # normaliza os arquivos de texto para LF. Admitir apenas essa diferença
    # de terminador preserva a integridade do conteúdo em ambos os sistemas.
    if caminho.suffix.lower() in {'.csv', '.json'}:
        lf = bruto.replace(b'\r\n', b'\n')
        hashes.add(hashlib.sha256(lf).hexdigest())
        hashes.add(hashlib.sha256(lf.replace(b'\n', b'\r\n')).hexdigest())
    if not esperado or esperado not in hashes:
        raise ValueError(f'Integridade da referência de segurança divergente: {caminho.name}.')
    return 'VERIFICADA'
