"""Confirmações parciais do colaborador, vinculadas a uma única unidade."""
from __future__ import annotations

from motor_pontuacao import MotorPontuacao, fator
from processamento import numero


# A confirmação de uma declaração não equivale a vistoria ou calibração estatística.
NUMERICOS = {
    'contentsValue': ('bens_ponderados', 'Bens e equipamentos, sem estoque (R$)', 'Valores'),
    'equipmentValue': ('equipamentos_ponderados', 'Parcela desses bens que é equipamento elétrico (R$)', 'Valores'),
    'stockValue': ('estoque_medio_estimado', 'Estoque nesta unidade (R$)', 'Valores'),
    'buildingValue': ('valor_predio_reposicao_brl', 'Reconstrução do imóvel, sem terreno (R$)', 'Imóvel'),
    'glassValue': ('valor_vidros_reposicao_brl', 'Reposição de vidros e espelhos (R$)', 'Vidros'),
    'employees': ('funcionarios_unidade_confirmados', 'Quantos empregados trabalham nesta unidade?', 'Equipe'),
    'payroll': ('folha_pagamento_mensal', 'Folha mensal desta unidade (R$)', 'Equipe'),
    'monthlyExpenses': ('despesa_fixa_mensal_estimada', 'Despesas fixas mensais desta unidade (R$)', 'Valores'),
    'monthlyRevenue': ('faturamento_mensal', 'Faturamento mensal da empresa inteira (R$)', 'Valores'),
    'rentValue': ('valor_aluguel_recorrente', 'Aluguel mensal desta unidade (R$)', 'Imóvel'),
}
ESCOLHAS = {
    'protection': ('escopo_protecao', 'O cliente quer proteger o quê?', 'Imóvel',
                   [('both', 'Imóvel e conteúdo'), ('building', 'Somente o imóvel'), ('contents', 'Somente o conteúdo')]),
    'propertyRelation': ('relacao_imovel_confirmada', 'O cliente é proprietário ou inquilino?', 'Imóvel',
                         [('owner', 'Proprietário'), ('tenant', 'Inquilino')]),
    'propertyStatus': ('situacao_imovel_cadastral', 'Qual é a situação atual do imóvel?', 'Imóvel',
                       [('REGULAR', 'Regular e em uso'), ('EM_OBRA', 'Em obra ou reforma'), ('CONDENADO', 'Condenado ou interditado')]),
    'wallMaterial': ('material_parede_externa_cadastrado', 'Qual é o material predominante das paredes externas?', 'Imóvel',
                     [('ALVENARIA', 'Alvenaria'), ('CONCRETO', 'Concreto'), ('MADEIRA', 'Madeira'), ('MATERIAL_COMBUSTIVEL', 'Outro material combustível')]),
}
PERGUNTAS = {
    'securityControls': ('O local tem alarme monitorado e controle de acesso em funcionamento?', 'Proteção'),
    'portableGoods': ('Há mercadorias ou equipamentos de fácil transporte e revenda?', 'Proteção'),
    'roofMaintained': ('O telhado e suas fixações foram inspecionados e estão em bom estado?', 'Proteção'),
    'exposedAssets': ('Há bens ou equipamentos em áreas externas expostas ao vento?', 'Proteção'),
    'hazardousWork': ('Os empregados trabalham com máquinas, calor, químicos, altura ou esforço físico frequente?', 'Equipe'),
    'hasGlass': ('Existem vidros, espelhos ou vitrines que precisam de proteção?', 'Vidros'),
    'glassExposed': ('Esses vidros ficam expostos à rua, à circulação de pessoas ou a impactos?', 'Vidros'),
}
ORIGEM = 'Confirmado pelo colaborador com o cliente nesta análise'


def aplicar_complemento(record, complemento):
    if not isinstance(complemento, dict) or set(complemento) - (set(NUMERICOS) | set(ESCOLHAS) | set(PERGUNTAS)):
        raise ValueError('Dados complementares inválidos. Utilize os campos do formulário.')
    record = dict(record)
    origins = {k: 'Cadastro BB/Datathon' for k in record}
    confirmed = {}
    for key, value in complemento.items():
        if value is None or value == '':
            continue
        if key in NUMERICOS:
            n = numero(value)
            if isinstance(value, bool) or n is None or n > 1e12:
                raise ValueError('Informe um número positivo ou zero: ' + NUMERICOS[key][1])
            if key == 'employees' and (n != int(n) or n > 1000000):
                raise ValueError('A quantidade de empregados deve ser um inteiro entre zero e um milhão.')
            confirmed[key] = n
            column = NUMERICOS[key][0]
            record[column] = n
            origins[column] = ORIGEM
        elif key in ESCOLHAS:
            column, label, _, options = ESCOLHAS[key]
            if not isinstance(value, str) or value not in dict(options):
                raise ValueError('Escolha uma opção válida: ' + label)
            confirmed[key] = record[column] = value
            origins[column] = ORIGEM
        else:
            if type(value) is not bool:
                raise ValueError('Confirme Sim, Não ou deixe Ainda não sei: ' + PERGUNTAS[key][0])
            confirmed[key] = value

    q = {k: v for k, v in confirmed.items() if k in PERGUNTAS}
    if 'employees' in confirmed:
        q['hasEmployees'] = confirmed['employees'] > 0
    if q.get('hasEmployees') is False:
        if q.get('hazardousWork') is True or confirmed.get('payroll', 0) > 0:
            raise ValueError('Sem empregados nesta unidade, tarefas de empregados e folha positiva são incompatíveis.')
        q['hazardousWork'] = False
        record['folha_pagamento_mensal'] = 0
        origins['folha_pagamento_mensal'] = ORIGEM
    if q.get('hasGlass') is False:
        if q.get('glassExposed') is True or confirmed.get('glassValue', 0) > 0:
            raise ValueError('Sem vidros a proteger, exposição de vidros e reposição positiva são incompatíveis.')
        q['glassExposed'] = False
        record['valor_vidros_reposicao_brl'] = 0
        origins['valor_vidros_reposicao_brl'] = ORIGEM
    for key, column in [('hasGlass', 'possui_vidros_confirmado'), ('hasEmployees', 'possui_empregados_confirmado')]:
        if key in q:
            record[column] = 'SIM' if q[key] else 'NAO'
            origins[column] = ORIGEM
    if 'contentsValue' in confirmed:
        record['bens_total_referencia'] = confirmed['contentsValue']
        record['confianca_bens'] = .85
        origins['bens_total_referencia'] = ORIGEM
    if 'equipmentValue' in confirmed:
        record['equipamentos_total_referencia'] = confirmed['equipmentValue']
        origins['equipamentos_total_referencia'] = ORIGEM
    if {'contentsValue', 'equipmentValue'} & confirmed.keys():
        for key in ('informatica_ponderada', 'eletronicos_ponderados', 'letreiros_ponderados', 'tipos_bens_cadastrados'):
            record.pop(key, None)
    for equipment, total in [('equipamentos_ponderados', 'bens_ponderados'), ('equipamentos_total_referencia', 'bens_total_referencia')]:
        a, b = numero(record.get(equipment)), numero(record.get(total))
        if a is not None and b is not None and a > b:
            raise ValueError('Equipamentos fazem parte dos bens. Confirme os dois valores; equipamentos não podem superar o total sem estoque.')
    if 'stockValue' in confirmed:
        record['estoque_pico_estimado'] = confirmed['stockValue']
        origins['estoque_pico_estimado'] = ORIGEM
    if 'rentValue' in confirmed:
        record['pagamento_aluguel_recorrente'] = 'SIM' if confirmed['rentValue'] > 0 else 'NAO'
        origins['pagamento_aluguel_recorrente'] = ORIGEM
    if confirmed.get('protection') == 'contents':
        record['valor_predio_reposicao_brl'] = 0
        origins['valor_predio_reposicao_brl'] = 'Imóvel fora do escopo confirmado'
    elif confirmed.get('protection') == 'building':
        for column in ('bens_ponderados', 'bens_total_referencia', 'equipamentos_ponderados', 'equipamentos_total_referencia', 'estoque_medio_estimado', 'estoque_pico_estimado'):
            record[column] = 0
            origins[column] = 'Conteúdo fora do escopo confirmado'
    if q:
        record['questionario'] = q
    record['_complemento_colaborador'] = confirmed
    record['_origens'] = origins
    return record, origins, q, confirmed


class MotorComplemento(MotorPontuacao):
    """Aplica apenas respostas conhecidas; perguntas vazias preservam a incerteza."""
    def fatores(self, r):
        factors = super().fatores(r)
        q = r.get('questionario') or {}
        for name, changes in [
            ('exposicao_territorial', [('securityControls', .15, True), ('portableGoods', .15, False)]),
            ('atividade_ocupacional', [('hazardousWork', .3, False)]),
        ]:
            known = [(key, weight, inverse) for key, weight, inverse in changes if type(q.get(key)) is bool]
            if not known:
                continue
            original = factors[name]
            weight = sum(w for _, w, _ in known)
            value = (1 - weight) * original.valor_normalizado + sum(w * (not q[k] if inverse else q[k]) for k, w, inverse in known)
            factors[name] = fator(original.nome, {'cadastro': original.valor_original, **{k:q[k] for k, _, _ in known}},
                                  value, (1 - weight) * original.confianca + weight * .8,
                                  'Combinação do fator cadastral com as respostas confirmadas, nos pesos do formulário MVP',
                                  original.observacao + ' Declaração do cliente registrada pelo colaborador.')
        if q.get('hasGlass') is True and type(q.get('glassExposed')) is bool:
            factors['presenca_loja'] = fator('Vidros e exposição confirmados',
                {'hasGlass': True, 'glassExposed': q['glassExposed']}, .6 + .4 * q['glassExposed'], .85,
                '0,60 + 0,40 × exposição a impactos', 'Declaração do cliente; não substitui vistoria.')
        return factors


def explicar_confianca(result, record, complemento=None):
    confirmed = complemento or {}
    fields = []
    for key, (column, label, group) in NUMERICOS.items():
        fields.append({'id':key, 'label':label, 'grupo':group, 'tipo':'number',
                       'valorCadastro':record.get(column), 'valorConfirmado':confirmed.get(key),
                       'inteiro':key == 'employees'})
    for key, (column, label, group, options) in ESCOLHAS.items():
        fields.append({'id':key, 'label':label, 'grupo':group, 'tipo':'select', 'opcoes':options,
                       'valorCadastro':record.get(column), 'valorConfirmado':confirmed.get(key)})
    for key, (label, group) in PERGUNTAS.items():
        fields.append({'id':key, 'label':label, 'grupo':group, 'tipo':'boolean',
                       'valorCadastro':None, 'valorConfirmado':confirmed.get(key)})
    irrelevant = set()
    if confirmed.get('hasGlass') is False:
        irrelevant.update(('glassValue', 'glassExposed'))
    if confirmed.get('employees') == 0:
        irrelevant.update(('payroll', 'hazardousWork'))
    if confirmed.get('protection') == 'contents':
        irrelevant.add('buildingValue')
    if confirmed.get('protection') == 'building':
        irrelevant.update(('contentsValue', 'equipmentValue', 'stockValue', 'securityControls', 'portableGoods'))
    for field in fields:
        field['aplicavel'] = field['id'] not in irrelevant
        field['pendente'] = field['aplicavel'] and field['id'] not in confirmed
    reasons = []
    def pending(*keys):
        return [f['id'] for f in fields if f['pendente'] and f['id'] in keys]
    for keys, text in [
        (('protection','wallMaterial','propertyStatus','propertyRelation'), 'Características e escopo do imóvel ainda precisam de confirmação com o cliente.'),
        (tuple(PERGUNTAS), 'Há perguntas sobre proteção, telhado, empregados ou vidros ainda sem resposta.'),
        (tuple(NUMERICOS), 'Valores de reposição e informações financeiras ou da equipe ainda não foram confirmados para esta análise.'),
    ]:
        ids = pending(*keys)
        if ids:
            reasons.append({'texto':text, 'campos':ids})
    limitations = ['Os pesos de confiança são regras experimentais do MVP. Responder ao formulário não garante confiança alta nem precisão estatística.']
    if numero(record.get('quantidade_unidades')) != 1:
        limitations.append('A empresa tem mais de uma unidade. O faturamento empresarial não é dividido entre filiais; a vulnerabilidade financeira continua limitada.')
    for source in result['fontes']:
        if not source['disponivel']:
            limitations.append('Referência de ' + {'seguranca':'segurança comercial','clima':'clima','nr4':'classificação ocupacional'}.get(source['tipo'], source['tipo']) + ' ausente ou inadequada. Respostas do cliente não substituem essa fonte externa.')
    return {'percentual':result['recomendacao']['confianca_geral'] * 100,
            'explicacao':'Este indicador resume a força das evidências usadas na recomendação. O cálculo combina a confiança das dez necessidades, com os pesos do modelo.',
            'motivos':reasons, 'limitacoes':limitations, 'campos':fields,
            'pendentes':sum(f['pendente'] for f in fields), 'confirmados':len(confirmed),
            'empresaId':record['empresa_id'], 'imovelId':record['imovel_id']}
