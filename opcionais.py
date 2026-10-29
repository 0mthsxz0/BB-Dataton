"""Triagem explicável de opcionais. Sinais nunca confirmam exposição ou aceitação."""
from processamento import numero


AGREGADOS = {
    'valor_bem_ponderado_referencia': ['bens_ponderados'],
    'valor_cadastrado': ['bens_total_referencia'],
    'nivel_confianca_vinculo': ['confianca_bens'],
    'tipo_bem': ['tipos_bens_cadastrados'],
}


def avaliar_opcionais(registro, regras):
    operacao = registro.get('operacao_confirmada', {})
    limite = regras['optionalThresholds']['estimatedOperation']
    positivos = lambda *campos: any((numero(registro.get(k)) or 0) > 0 for k in campos)
    pistas = {
        'refrigeration': (numero(registro.get('probabilidade_refrigeracao_referencia')) or 0) >= limite,
        'delivery': (numero(registro.get('probabilidade_delivery_referencia')) or 0) >= limite or positivos('percentual_receita_delivery_est'),
        'homeOffice': positivos('dependencia_digital_pct', 'percentual_vendas_online_estimado'),
        # Recebimentos não digitais não comprovam dinheiro em caixa.
        'cash': False, 'unrest': False, 'roadside': False, 'sprinklers': False,
        'records': positivos('dependencia_digital_pct', 'probabilidade_tratamento_dados'),
        'signage': positivos('letreiros_ponderados'),
        # Equipamento elétrico genérico não comprova equipamento eletrônico.
        'electronics': positivos('eletronicos_ponderados', 'informatica_ponderada'),
        'outdoors': False, 'garage': False, 'moral': False,
        'interruption': positivos('faturamento_mensal', 'despesa_fixa_mensal_estimada'),
    }
    resultado = []
    for extra in regras['optional']:
        item = dict(extra)
        chave = extra['operation']
        confirmado = operacao.get(chave)
        evidencias, usados = [], set()
        for origem in extra['fields']:
            campos = list(AGREGADOS.get(origem['field'], [origem['field']]))
            if origem['field'] == 'valor_bem_ponderado_referencia':
                if extra['code'] == 'EQUIPAMENTOS_ELETRONICOS':
                    campos += ['informatica_ponderada', 'eletronicos_ponderados']
                elif extra['code'] == 'ANUNCIOS_LUMINOSOS':
                    campos += ['letreiros_ponderados']
            for campo in campos:
                valor = registro.get(campo)
                if valor is None or valor == '' or campo in usados:
                    continue
                usados.add(campo)
                if isinstance(valor, (int, float)) and numero(valor) is None:
                    continue
                evidencias.append({'arquivo': origem['table'] + '.csv', 'campo': campo,
                    'campo_origem': origem['field'], 'valor': valor,
                    'origem': registro.get('_origens', {}).get(campo, 'Cadastro agregado da unidade' if campo in sum(AGREGADOS.values(), []) + ['informatica_ponderada', 'eletronicos_ponderados', 'letreiros_ponderados'] else 'Cadastro Datathon'),
                    'derivacao': 'Soma por empresa e unidade; valor cadastrado × probabilidade uma única vez.' if campo.endswith('_ponderados') or campo == 'informatica_ponderada' else None})
        if confirmado is not None:
            evidencias.insert(0, {'arquivo': None, 'campo': 'operations.' + chave,
                'valor': confirmado, 'origem': 'Confirmado no formulário', 'derivacao': None})
        candidato = confirmado is True or (confirmado is None and pistas[chave])
        # Somente delivery/refrigeração mantêm a sugestão provisória histórica.
        sugerida = confirmado is True or (confirmado is None and chave in ('refrigeration', 'delivery') and pistas[chave])
        item.update(confirmacao=confirmado, candidata=candidato, sugerida=sugerida,
            sinal_estimado=numero(registro.get({'refrigeration':'probabilidade_refrigeracao_referencia', 'delivery':'probabilidade_delivery_referencia'}.get(chave, ''))),
            evidencias=evidencias, pergunta=extra['question'],
            estado='CONFIRMADO' if confirmado is True else 'AUSENCIA_CONFIRMADA' if confirmado is False else 'CONFIRMAR_EXPOSICAO' if candidato else 'SEM_EVIDENCIA_SUFICIENTE',
            confianca='Declarado pelo usuário; sem vistoria' if confirmado is not None else 'Indício indireto; exposição não confirmada' if candidato else 'Sem confirmação da exposição',
            motivo='Operação confirmada pelo usuário; compatibilidade contratual ainda deve ser validada.' if confirmado is True else 'Ausência confirmada pelo usuário; não sugerir inclusão.' if confirmado is False else extra['explanation'],
            disponibilidade='SUJEITA_A_ATIVIDADE_E_ACEITACAO' if len(extra['plans']) < 3 else 'SUJEITA_A_CONDICOES')
        resultado.append(item)
    return resultado


def comparar_alternativas(recomendacao, adicionais):
    """Compara adequação; opcionais não substituem índices nem alteram a aderência."""
    relevantes = [x for x in adicionais if x['candidata'] or x.get('solicitada')]
    resultado = []
    for c in recomendacao['comparacao']:
        plano = c['plano']
        compativeis = [x for x in relevantes if plano in x['plans']]
        incompat = [x['name'] for x in relevantes if plano not in x['plans'] and (x['confirmacao'] is True or x.get('solicitada'))]
        apto = c['apto_simulacao'] and not incompat and not recomendacao['indicacao_bloqueada']
        resultado.append({'plano': plano, 'adequado': apto, 'aderencia_percentual': c['aderencia_percentual'],
            'lacunas': c['indispensaveis_ausentes'], 'opcionais_incompativeis': incompat,
            'opcionais_para_avaliar': [x['code'] for x in compativeis],
            'exposicoes_pendentes': [x['code'] for x in compativeis if x['confirmacao'] is None],
            'motivo': 'Alternativa de proteção; confirmar exposição, escopo, limites, franquias e preço.' if apto else 'Não atende à meta, às prioridades ou à compatibilidade das exposições confirmadas; confira as lacunas.',
            'preco': None})
    return resultado
