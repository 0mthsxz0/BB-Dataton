"""Adaptador local do formulário para o motor do MVP. Não persiste propostas."""
from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path

import pandas as pd
import requests

from localizacao import aplicar_localizacao
from motor_pontuacao import MotorPontuacao, fator, carregar_config
from processamento import carregar_base, localizar_dados, caminho_referencia, numero
from recomendador import recomendar_plano
from referencias import classe_cnae
from perfil_cnae import perfil_cnae, CAMPOS as CAMPOS_PERFIL
from produto import REGRAS, adaptar_catalogo, personalizar
from rastreabilidade import anexar_evidencias

ROOT = Path(__file__).parent
PUBLIC = ROOT / 'frontend' / 'public'
QUESTIONNAIRE = json.loads((PUBLIC / 'questionnaire.json').read_text(encoding='utf-8'))
QUESTION_IDS = [q['id'] for g in QUESTIONNAIRE['groups'] for q in g['questions']]
PLAN_IDS = {'ESSENCIAL': '892', 'PRATICO': '893', 'TOTAL': '894'}
# Contextual groups from the existing MVP, not a conversion to CNAE.
ACTIVITY_GROUPS = {'625':'RESTAURANTE','476':'FARMACIA','909':'MERCADO','484':'VAREJO_MODA',
                   '690':'CLINICA','641':'BELEZA','728':'ESCOLA_CURSO','674':'ESCRITORIO','1007':'ELETRONICOS'}
# Explicit fields only. Blanks inherit a BB value; numeric zero overrides it.
NUMBER_FIELDS = {
    'contentsValue': 'bens_ponderados', 'equipmentValue': 'equipamentos_ponderados',
    'stockValue': 'estoque_medio_estimado', 'glassValue': 'valor_vidros_reposicao_brl',
    'buildingValue': 'valor_predio_reposicao_brl', 'payroll': 'folha_pagamento_mensal',
    'monthlyExpenses': 'despesa_fixa_mensal_estimada', 'monthlyRevenue': 'faturamento_mensal',
    'employees': 'funcionarios_unidade_confirmados', 'rentValue': 'valor_aluguel_recorrente',
    'units': 'quantidade_unidades',
}


def normalizar(value):
    text = unicodedata.normalize('NFD', str(value or '')).lower()
    return ''.join(c for c in text if not unicodedata.combining(c)).strip()


def base_opcional():
    try:
        pasta = localizar_dados()
    except ValueError:
        return None
    # A present but invalid dataset must not silently disappear.
    return carregar_base(pasta)


def contexto(base=None):
    base = base if base is not None else base_opcional()
    rows = [] if base is None else [
        {'empresaId': r['empresa_id'], 'imovelId': r['imovel_id'],
         'city': r['municipio_real'], 'uf': r['uf_real'],
         'label': f"{r['empresa_id']} / {r['imovel_id']} · {r['municipio_real']} / {r['uf_real']} · {r.get('grupo_atividade', '')}"}
        for r in base.estabelecimentos.to_dict('records')]
    return {'baseDisponivel': base is not None, 'estabelecimentos': rows,
            'aviso': 'Base local do Datathon. Não é uma conexão com sistemas bancários de produção.'}


def consultar_perfil_cnae(payload,base=None):
    return perfil_cnae(payload,base if base is not None else base_opcional())


def consultar_municipio(city, uf):
    if not re.fullmatch(r'[A-Z]{2}', str(uf)) or not isinstance(city, str) or not 2 <= len(city) <= 100:
        raise ValueError('Informe cidade e UF válidas.')
    url = f'https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios'
    try:
        response = requests.get(url, timeout=(3, 7))
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            raise ValueError('Resposta IBGE inválida.')
        found = next((r for r in rows if normalizar(r.get('nome')) == normalizar(city)), None)
        if found is None:
            raise ValueError('Cidade não encontrada na UF pelo IBGE. Confira a grafia.')
        return {'codigo_ibge_municipio': str(found['id']), 'municipio_real': found['nome'],
                'uf_real': uf, 'fonte_localizacao': url}, []
    except (requests.RequestException, requests.exceptions.JSONDecodeError):
        # Exact city + UF only. No guessed municipality, postal region or street risk.
        codes = dict(zip('RO AC AM RR PA AP TO MA PI CE RN PB PE AL SE BA MG ES RJ SP PR SC RS MS MT GO DF'.split(),
                         '11 12 13 14 15 16 17 21 22 23 24 25 26 27 28 29 31 32 33 35 41 42 43 50 51 52 53'.split()))
        for filename in ('seguranca_municipal.csv', 'clima_municipal.csv'):
            snapshot = caminho_referencia(filename)
            if not snapshot.exists():
                continue
            rows = pd.read_csv(snapshot, dtype=str)
            for row in rows.to_dict('records'):
                name = re.sub(r'\s+-\s+[A-Z]{2}$', '', str(row.get('municipio', '')))
                code = str(row.get('codigo_ibge_municipio', ''))
                if normalizar(name) == normalizar(city) and len(code) == 7 and code.startswith(codes.get(uf, '!')):
                    return {'codigo_ibge_municipio': code, 'municipio_real': name, 'uf_real': uf,
                            'fonte_localizacao': f'Snapshot público distribuído: {filename}'}, [
                        'API do IBGE indisponível nesta consulta. Município confirmado pelo nome e UF no snapshot público distribuído.']
        return {'codigo_ibge_municipio': '', 'municipio_real': city, 'uf_real': uf}, [
            'API do IBGE indisponível. Sem vínculo municipal confirmado, referências territoriais não serão utilizadas.']


def validar(payload):
    if not isinstance(payload, dict):
        raise ValueError('Envie um objeto JSON.')
    validar_personalizacao(payload)
    catalog = json.loads((PUBLIC / 'activities.json').read_text(encoding='utf-8'))
    activity = next((a for a in catalog['activities'] if a['id'] == payload.get('activityId')), None)
    if activity is None:
        raise ValueError('Escolha uma atividade real do catálogo.')
    sub = payload.get('subactivityId')
    if sub == 'other':
        if not isinstance(payload.get('otherSubactivity'), str) or not 4 <= len(payload['otherSubactivity'].strip()) <= 300:
            raise ValueError('Descreva a subatividade para revisão.')
    elif not any(s['id'] == sub for s in activity['subactivities']):
        raise ValueError('A subatividade não pertence à atividade escolhida.')
    answers = payload.get('answers')
    if not isinstance(answers, dict) or any(k not in answers or (type(answers[k]) is not bool and not (k == 'hasEmployees' and answers[k] is None)) for k in QUESTION_IDS):
        raise ValueError('Responda às perguntas sobre proteção. A presença de empregados pode ficar desconhecida quando a quantidade não for informada.')
    if answers['hasEmployees'] is False and answers['hazardousWork']:
        raise ValueError('Sem empregados, responda Não à pergunta sobre tarefas dos empregados.')
    if not answers['hasGlass'] and answers['glassExposed']:
        raise ValueError('Sem vidros, responda Não à pergunta sobre exposição dos vidros.')
    if payload.get('protection') not in ('both', 'contents', 'building'):
        raise ValueError('Informe o que deseja proteger.')
    if payload.get('shopping') not in ('yes', 'no', 'building', 'gallery'):
        raise ValueError('Informe se a empresa fica em shopping, prédio comercial, galeria protegida ou nenhum desses locais.')
    for k in NUMBER_FIELDS:
        v = payload.get(k)
        if v is not None and v != '':
            if isinstance(v, bool) or numero(v) is None or float(v) > 1e12:
                raise ValueError(f'Valor inválido no campo {k}. Use número positivo ou zero.')
            if k in ('employees','units') and (float(v) != int(float(v)) or float(v) > 1000000 or k == 'units' and float(v) < 1):
                raise ValueError('Quantidade de empregados/unidades deve ser um inteiro válido; unidades deve ser pelo menos um.')
    employee_count = numero(payload.get('employees'))
    if employee_count is not None and answers['hasEmployees'] is not None and answers['hasEmployees'] != (employee_count > 0):
        raise ValueError('A quantidade de empregados não combina com a presença declarada de empregados.')
    if employee_count == 0 and answers['hazardousWork']:
        raise ValueError('Sem empregados, não há tarefas dos empregados a confirmar.')
    glass_count = payload.get('glassCount')
    if glass_count is not None and glass_count != '':
        value = numero(glass_count)
        if isinstance(glass_count, bool) or value is None or value != int(value) or value > 1000000:
            raise ValueError('Informe uma quantidade inteira de itens de vidro ou deixe em branco.')
        if (value == 0) == answers['hasGlass']:
            raise ValueError('A quantidade de itens de vidro não combina com a resposta sobre ter vidros para proteger.')
    profile_fields = payload.get('profileFields', [])
    if not isinstance(profile_fields,list) or any(not isinstance(k,str) or k not in CAMPOS_PERFIL for k in profile_fields):
        raise ValueError('Campos de referência da atividade inválidos.')
    cnae = payload.get('cnae')
    if cnae and (not isinstance(cnae, str) or not re.fullmatch(r'\d{4}-?\d/?\d{2}', cnae)):
        raise ValueError('Informe um CNAE de sete dígitos.')
    return activity


def validar_personalizacao(payload):
    operations = payload.get('operations', {})
    if not isinstance(operations, dict) or set(operations) - set(REGRAS['operations']) or any(type(v) is not bool and v is not None for v in operations.values()):
        raise ValueError('Confirmações operacionais inválidas.')
    if operations.get('shoppingControls') is True and payload.get('shopping') != 'yes':
        raise ValueError('Requisitos de shopping só podem ser confirmados para estabelecimento em shopping.')
    if type(payload.get('termYears', 1)) is not int or payload.get('termYears', 1) not in (1,2,3,4,5):
        raise ValueError('Vigência deve ser de um a cinco anos.')
    if payload.get('priority', 'equilibrada') not in ('equilibrada','patrimonio','continuidade','terceiros'):
        raise ValueError('Prioridade inválida.')
    plan = payload.get('selectedPlan')
    if plan is not None and plan not in REGRAS['plans']:
        raise ValueError('Plano inválido.')
    adjustments = payload.get('coverageAdjustments', {})
    if not isinstance(adjustments, dict) or set(adjustments) - {'include','exclude'}:
        raise ValueError('Ajustes de coberturas inválidos.')
    for field, allowed in [('include', REGRAS['adjustable']), ('exclude', REGRAS['adjustable'])]:
        values = adjustments.get(field, [])
        if not isinstance(values, list) or any(not isinstance(v, str) or v not in allowed for v in values) or len(values) != len(set(values)):
            raise ValueError('Ajuste inválido: as seis obrigatórias devem ser preservadas.')
    if set(adjustments.get('include', [])) & set(adjustments.get('exclude', [])):
        raise ValueError('Uma cobertura não pode ser incluída e excluída simultaneamente.')
    if plan == 'ESSENCIAL' and (adjustments.get('include') or adjustments.get('exclude')):
        raise ValueError('Nesta política do guia, ajustes das quatro coberturas são feitos no Prático ou Total.')
    for field, allowed in [('indispensable', list(REGRAS['mandatory']) + REGRAS['adjustable']),
                           ('optionalCovers', [x['code'] for x in REGRAS['optional']]), ('optionalExclusions', [x['code'] for x in REGRAS['optional']])]:
        values = payload.get(field, [])
        if not isinstance(values, list) or any(not isinstance(v, str) or v not in allowed for v in values) or len(values) != len(set(values)):
            raise ValueError('Lista de preferências inválida: ' + field)
    if payload.get('propertyRelation') not in (None, '', 'owner', 'tenant'):
        raise ValueError('Relação com o imóvel inválida.')
    if payload.get('propertyStatus') not in (None, '', 'REGULAR', 'EM_OBRA', 'CONDENADO'):
        raise ValueError('Situação do imóvel inválida.')
    if payload.get('wallMaterial') not in (None, '', 'ALVENARIA', 'CONCRETO', 'MADEIRA', 'MATERIAL_COMBUSTIVEL'):
        raise ValueError('Material das paredes inválido.')


class MotorFormulario(MotorPontuacao):
    """Mesma fórmula do MVP, com fatores declarados pelas oito respostas."""
    def fatores(self, r):
        f = super().fatores(r)
        q = r['questionario']
        original = f['exposicao_territorial']
        # No evidence remains neutral at 0.5 and has zero source confidence.
        value = .7 * original.valor_normalizado + .15 * (not q['securityControls']) + .15 * q['portableGoods']
        f['exposicao_territorial'] = fator('Território e condições de subtração',
            {'territorio': original.valor_original, 'securityControls': q['securityControls'], 'portableGoods': q['portableGoods']},
            value, .7 * original.confianca + .3 * .8,
            '0,70 × exposição territorial + 0,15 × ausência de controles + 0,15 × bens transportáveis', original.observacao)
        original = f['atividade_ocupacional']
        f['atividade_ocupacional'] = fator('Atividade e tarefas dos empregados',
            {'grau_nr4': original.valor_original, 'hazardousWork': q['hazardousWork']},
            .7 * original.valor_normalizado + .3 * q['hazardousWork'], .7 * original.confianca + .3 * .8,
            '0,70 × classificação ocupacional + 0,30 × tarefas com exposição informada', original.observacao)
        f['presenca_loja'] = fator('Vidros e exposição a impactos',
            {'hasGlass': q['hasGlass'], 'glassExposed': q['glassExposed']},
            (.6 + .4 * q['glassExposed']) if q['hasGlass'] else 0, .85,
            'Com vidros: 0,60 + 0,40 × exposição a impactos; sem vidros: zero',
            'Confirmação do usuário; não é vistoria do imóvel.')
        return f


def analisar(payload, base=None, municipio_fn=consultar_municipio):
    activity = validar(payload)
    base = base if base is not None else base_opcional()
    has_link = bool(payload.get('empresaId') or payload.get('imovelId'))
    if has_link and base is None:
        raise ValueError('Base do Datathon indisponível para esse vínculo.')
    record = base.registro(payload.get('empresaId'), payload.get('imovelId')) if has_link else {}
    warnings = []
    origins = {k: 'Cadastro BB/Datathon' for k in record}
    # Validate city and UF even when no network operation is needed.
    city, uf = payload.get('city'), payload.get('uf')
    if not isinstance(city, str) or not 2 <= len(city.strip()) <= 100 or uf not in 'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split():
        raise ValueError('Informe cidade e UF válidas.')
    if has_link and normalizar(city) == normalizar(record.get('municipio_real')) and uf == record.get('uf_real'):
        local = {k: record[k] for k in ('codigo_ibge_municipio', 'municipio_real', 'uf_real')}
        local['fonte_localizacao'] = 'Código municipal do cadastro BB/Datathon'
    else:
        local, notices = municipio_fn(city.strip(), uf)
        warnings.extend(notices)
    record, notices = aplicar_localizacao(record, local)
    warnings.extend(notices)
    for key, column in NUMBER_FIELDS.items():
        value = payload.get(key)
        if value is not None and value != '':
            record[column] = float(value)
            origins[column] = 'Informado no formulário'
            if key in ('contentsValue', 'equipmentValue'):
                for aggregate in ('informatica_ponderada', 'eletronicos_ponderados', 'letreiros_ponderados', 'tipos_bens_cadastrados'):
                    record.pop(aggregate, None)
            if key == 'contentsValue':
                record['bens_total_referencia'] = float(value)
                record['confianca_bens'] = .85
                origins['bens_total_referencia'] = 'Informado no formulário'
            if key == 'equipmentValue':
                record['equipamentos_total_referencia'] = float(value)
                origins['equipamentos_total_referencia'] = 'Informado no formulário'
            if key == 'stockValue':
                record['estoque_pico_estimado'] = float(value)
                origins['estoque_pico_estimado'] = 'Informado no formulário'
    profile_fields = payload.get('profileFields', [])
    if profile_fields:
        profile = perfil_cnae({'cnae':payload.get('cnae')},base)
        for key in profile_fields:
            if key not in profile['valores'] or numero(payload.get(key)) != profile['valores'][key]:
                raise ValueError('O perfil da atividade mudou. Consulte a referência novamente ou revise os valores.')
            origins[NUMBER_FIELDS[key]] = 'Estimativa do perfil agregado da atividade: ' + profile['cnae'] + '; mediana, não confirmação do cliente'
        if 'contentsValue' in profile_fields:
            record['confianca_bens'] = .35
            origins['bens_total_referencia'] = origins['bens_ponderados']
        if 'equipmentValue' in profile_fields:origins['equipamentos_total_referencia'] = origins['equipamentos_ponderados']
        if 'stockValue' in profile_fields:origins['estoque_pico_estimado'] = origins['estoque_medio_estimado']
        record['_perfil_cnae'] = {k: profile[k] for k in ('cnae', 'amostra', 'metodo', 'origem')}
        warnings.append('Foram usados valores estimados do perfil da atividade. Eles precisam de confirmação antes da cotação oficial.')
    if numero(record.get('equipamentos_ponderados')) is not None and numero(record.get('bens_ponderados')) is not None and record['equipamentos_ponderados'] > record['bens_ponderados']:
        raise ValueError('Equipamentos fazem parte dos bens: seu valor não pode superar o total dos bens sem estoque.')
    if numero(record.get('equipamentos_total_referencia')) is not None and numero(record.get('bens_total_referencia')) is not None and record['equipamentos_total_referencia'] > record['bens_total_referencia']:
        raise ValueError('O inventário de equipamentos herdado supera o total confirmado. Informe também o valor dos equipamentos para atualizar a parcela.')
    if payload.get('glassCount') not in (None, ''):
        record['quantidade_vidros_declarada'] = int(float(payload['glassCount']))
        origins['quantidade_vidros_declarada'] = 'Quantidade aproximada declarada no formulário; não é valor de reposição'
    q = dict(payload['answers'])
    employee_count = numero(payload.get('employees'))
    if employee_count is not None:
        q['hasEmployees'] = employee_count > 0
    record['questionario'] = q
    record['escopo_protecao'] = payload['protection']
    record['grupo_atividade'] = ACTIVITY_GROUPS.get(activity['id'])
    origins['grupo_atividade'] = 'Mapa contextual da atividade selecionada no formulário'
    record['possui_vidros_confirmado'] = 'SIM' if q['hasGlass'] else 'NAO'
    record['possui_empregados_confirmado'] = None if q['hasEmployees'] is None else 'SIM' if q['hasEmployees'] else 'NAO'
    origins['possui_vidros_confirmado'] = origins['possui_empregados_confirmado'] = 'Declarado nas oito perguntas do formulário'
    if q['hasEmployees'] is None:
        warnings.append('Quantidade de empregados nesta unidade ainda não informada; ausência não foi presumida.')
    if q['hasEmployees'] is False:
        if numero(payload.get('employees')) not in (None, 0) or numero(payload.get('payroll')) not in (None, 0):
            raise ValueError('Sem empregados, quantidade e folha devem ficar vazias ou ser zero.')
        record['funcionarios_unidade_confirmados'] = record['folha_pagamento_mensal'] = 0
        origins['funcionarios_unidade_confirmados'] = origins['folha_pagamento_mensal'] = 'Ausência confirmada no questionário'
    if not q['hasGlass']:
        if numero(payload.get('glassValue')) not in (None, 0):
            raise ValueError('Sem vidros, o valor de reposição deve ficar vazio ou ser zero.')
        record['valor_vidros_reposicao_brl'] = 0
        origins['valor_vidros_reposicao_brl'] = 'Ausência confirmada no questionário'
    if payload.get('protection') == 'building':
        for k in ('bens_ponderados', 'bens_total_referencia', 'equipamentos_ponderados',
                  'equipamentos_total_referencia', 'estoque_medio_estimado', 'estoque_pico_estimado'):
            record[k] = 0
            origins[k] = 'Conteúdo excluído pelo escopo somente imóvel'
        warnings.append('Somente imóvel: conteúdo e estoque excluídos do cenário financeiro.')
    elif payload.get('protection') == 'contents':
        record['valor_predio_reposicao_brl'] = 0
        origins['valor_predio_reposicao_brl'] = 'Imóvel excluído pelo escopo somente conteúdo'
    if payload.get('rentValue') not in ('', None):
        record['pagamento_aluguel_recorrente'] = 'SIM' if float(payload['rentValue']) > 0 else 'NAO'
        origins['pagamento_aluguel_recorrente'] = 'Derivado do aluguel informado no formulário'
    record['possui_termo_galeria'] = 'SIM' if payload.get('shopping') in ('yes', 'gallery') else 'NAO'
    record['tipo_local_funcionamento_declarado'] = payload.get('shopping')
    origins['possui_termo_galeria'] = 'Informado no formulário'
    # Insurer activity IDs are never converted into a CNAE by guesswork.
    if payload.get('cnae'):
        record['cnae_principal'] = payload['cnae']
        origins['cnae_principal'] = 'Informado no formulário'
        for key in ('grau_risco_nr4','fonte_nr4','versao_nr4','classe_cnae','descricao_nr4','pagina','sha256_documento'):
            record.pop(key, None)
        nr4 = caminho_referencia('nr4_cnae.csv')
        if nr4.exists():
            refs = pd.read_csv(nr4, dtype=str)
            rows = refs.loc[refs.classe_cnae.eq(classe_cnae(payload['cnae']))]
            if len(rows) == 1:
                record.update(rows.iloc[0].to_dict())
    if not record.get('cnae_principal'):
        warnings.append('Sem CNAE informado: referência ocupacional NR-4 desconhecida. Código de atividade da seguradora não equivale a CNAE.')
    elif has_link and not payload.get('cnae'):
        warnings.append('CNAE herdado do cadastro vinculado. Confirme sua correspondência com a atividade escolhida no formulário.')
    if not has_link:
        warnings.append('Sem vínculo com a base: cálculo usa apenas formulário e referências disponíveis. Campos vazios permanecem desconhecidos.')
    if numero(record.get('bens_ponderados')) is None:
        warnings.append('Inventário de bens não informado; confirme valor de reposição.')
    cfg = carregar_config()
    record.update(operacao_confirmada=payload.get('operations', {}), vigencia_anos=payload.get('termYears', 1),
                  prioridade_cliente=payload.get('priority', 'equilibrada'),
                  coberturas_indispensaveis=payload.get('indispensable', []),
                  plano_escolhido=payload.get('selectedPlan'), ajustes_coberturas=payload.get('coverageAdjustments', {}),
                  adicionais_escolhidos=payload.get('optionalCovers', []), adicionais_recusados=payload.get('optionalExclusions', []))
    for key, column in [('propertyStatus','situacao_imovel_cadastral'),('wallMaterial','material_parede_externa_cadastrado'),('propertyRelation','relacao_imovel_confirmada')]:
        if payload.get(key):
            record[column] = payload[key]
            origins[column] = 'Informado no formulário'
    record['_campos_perfil'] = list(profile_fields)
    record['_origens'] = origins
    motor = MotorFormulario(config=cfg)
    return montar_resultado(record, motor, base.catalogo if base else None, activity, payload['subactivityId'], q, warnings, origins, has_link, base=base if has_link else None)


def montar_resultado(record, motor, catalog, activity, subactivity_id, q, warnings, origins, has_link, base=None):
    cfg = motor.config
    record = motor.preparar_registro(record)
    indices = motor.analisar_registro(record)
    common = [c for c in cfg['coberturas'] if c not in indices]
    # Use the supplied Datathon contract, when available; otherwise the effective 6/8/10 guide catalog.
    catalog = catalog if catalog is not None else pd.DataFrame([
        {'plano': p, 'cobertura_fixa': c} for p, cs in [
            ('ESSENCIAL', common), ('PRATICO', common + list(indices)[:2]),
            ('TOTAL', list(cfg['coberturas']))] for c in cs])
    catalog = adaptar_catalogo(catalog)
    recommendation = recomendar_plano(indices, catalog, cfg, record)
    if not record.get('plano_escolhido') and any(record.get('ajustes_coberturas', {}).values()) and recommendation['plano_recomendado'] == 'ESSENCIAL':
        raise ValueError('Escolha Prático ou Total para ajustar as quatro coberturas.')
    dimensions = motor.dimensionar_coberturas(record)
    evidence = anexar_evidencias(record, indices, dimensions, origins, base)
    personalization = personalizar(record, recommendation, dimensions)
    for p in recommendation['comparacao']:
        p['id'] = PLAN_IDS[p['plano']]
        p['coberturas'] = sorted(catalog.loc[catalog.plano.eq(p['plano']), 'cobertura_fixa'].tolist())
    sources = []
    for kind in ('seguranca', 'clima', 'nr4'):
        confidence = numero(record.get(f'confianca_{kind}_0_1'))
        sources.append({'tipo': kind, 'fonte': record.get(f'fonte_{kind}'),
                        'periodo': record.get(f'periodo_{kind}', record.get(f'versao_{kind}')),
                        'metodologia': record.get(f'metodologia_{kind}'),
                        'disponivel': numero(record.get({'seguranca': 'seguranca_da_cidade_0_1',
                            'clima': 'exposicao_climatica_0_1', 'nr4': 'grau_risco_nr4'}[kind])) is not None
                            and (kind == 'nr4' or confidence is not None and confidence > 0)})
        if kind == 'seguranca':
            sources[-1]['disponivel'] = indices['ROUBO_FURTO_ARROMBAMENTO']['qualidade_seguranca']['utilizavel']
            sources[-1]['qualidade'] = indices['ROUBO_FURTO_ARROMBAMENTO']['qualidade_seguranca']
    return clean({'versao': '0.4.0-formulario.2', 'modelo': 'Motor determinístico do MVP + guia item 10',
        'atividade': {'id': activity['id'], 'subactivityId': subactivity_id, 'cnaeUtilizado': record.get('cnae_principal')},
        'planoId': PLAN_IDS[personalization['pacote']['plano']], 'indices': indices,
        'recomendacao': recommendation, 'dimensionamento': dimensions, 'rastreabilidade': evidence,
        'contextoSeguranca': indices['ROUBO_FURTO_ARROMBAMENTO']['contexto_seguranca'],
        'avaliacaoMosler': indices['ROUBO_FURTO_ARROMBAMENTO']['avaliacao_mosler'],
        'personalizacao': personalization,
        'perfilAtividade': {'usado':bool(record.get('_campos_perfil')), 'campos':record.get('_campos_perfil',[])},
        'vidrosDeclarados': {'quantidade': record.get('quantidade_vidros_declarada'),
            'valorReposicaoPendente': numero(record.get('valor_vidros_reposicao_brl')) is None,
            'observacao': 'Quantidade declarada não é convertida automaticamente em custo de reposição.'},
        'patrimonio': {k: record.get(k) for k in ('bens_ponderados', 'bens_total_referencia',
            'equipamentos_ponderados', 'estoque_medio_estimado', 'valor_predio_reposicao_brl')},
        'origens': {k: origins.get(k, 'Não informado') for k in NUMBER_FIELDS.values()},
        'fontes': sources, 'avisos': warnings,
        'localizacao': {k: record.get(k) for k in ('codigo_ibge_municipio','municipio_real','uf_real','fonte_localizacao')},
        'respostas': q, 'vinculoBase': has_link,
        'observacao': 'Índices experimentais de prioridade. Não são probabilidades de sinistro, prêmio ou aceitação contratual.'})


def analisar_cadastro(payload, base=None):
    """Recomendação imediata do cadastro, sem simular respostas do usuário."""
    if not isinstance(payload, dict) or any(not isinstance(payload.get(k), str) or not 1 <= len(payload[k]) <= 100
                                            for k in ('empresaId', 'imovelId')):
        raise ValueError('Selecione uma empresa e um estabelecimento válidos.')
    base = base if base is not None else base_opcional()
    if base is None:
        raise ValueError('A base local do Datathon não está disponível.')
    record = base.registro(payload['empresaId'], payload['imovelId'])
    motor = MotorPontuacao()
    warnings = ['Análise inicial baseada somente no cadastro e nas referências disponíveis. As oito perguntas ainda não foram respondidas.',
                'Escopo de imóvel/conteúdo ainda não escolhido; valores de reconstrução e reposição devem ser confirmados.']
    for column, label in [('seguranca_da_cidade_0_1','segurança municipal'),('exposicao_climatica_0_1','clima'),('grau_risco_nr4','classificação ocupacional')]:
        if numero(record.get(column)) is None:
            warnings.append(f'Sem referência de {label} para esta unidade; componente desconhecido, com confiança reduzida.')
    result = montar_resultado(record, motor, base.catalogo, {'id':None}, None, None, warnings,
                             {k:'Cadastro BB/Datathon' for k in record}, True, base=base)
    fixed = {}
    for key,column,allowed in [('propertyStatus','situacao_imovel_cadastral',('REGULAR','EM_OBRA','CONDENADO')),('wallMaterial','material_parede_externa_cadastrado',('ALVENARIA','CONCRETO','MADEIRA','MATERIAL_COMBUSTIVEL'))]:
        if record.get(column) in allowed:fixed[key]=record[column]
    if record.get('possui_vidros_confirmado') in ('SIM','NAO'):fixed['hasGlass']='yes' if record['possui_vidros_confirmado']=='SIM' else 'no'
    if fixed.get('hasGlass') == 'no':fixed['glassExposed']='no'
    result.update(confirmacoesDisponiveis=fixed,preenchimento={key:record[col] for key,col in NUMBER_FIELDS.items() if numero(record.get(col)) is not None},preliminar=True, modelo='Motor original do MVP aplicado ao cadastro, sem respostas presumidas',
                  cadastro={k:record.get(k) for k in ('empresa_id','imovel_id','grupo_atividade','descricao_cnae','porte')},
                  dadosCadastrais={k:record.get(k) for k in ('bens_quantidade','bens_total_referencia','bens_ponderados',
                    'confianca_bens','estoque_medio_estimado','estoque_pico_estimado','quantidade_unidades',
                    'quantidade_funcionarios_estimada','folha_pagamento_mensal','despesa_fixa_mensal_estimada',
                    'faturamento_mensal','pagamento_aluguel_recorrente','valor_aluguel_recorrente',
                    'material_parede_externa_cadastrado','padrao_construtivo_cadastrado')})
    return clean(result)


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
