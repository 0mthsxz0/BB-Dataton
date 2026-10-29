"""Seleção de planos por adequação incremental e elegibilidade preliminar."""
from __future__ import annotations

from motor_pontuacao import DECISORIAS, COMUNS, MotorPontuacao, carregar_config
from processamento import NULOS
from produto import adaptar_catalogo, triagem

ORDEM_PLANOS = ['ESSENCIAL', 'PRATICO', 'TOTAL']


def verificar_elegibilidade(registro, config):
    """Não inventa exclusões por CNAE. Regras oficiais detalhadas continuam pendentes."""
    regras = config['elegibilidade']
    motivos = []
    if registro.get('situacao_imovel_cadastral') in regras['estados_validar']:
        motivos.append('Validar situação cadastral/obra e condições de uso do estabelecimento.')
    if registro.get('material_parede_externa_cadastrado') in regras['materiais_validar']:
        motivos.append('Validar predominância de material combustível nas paredes externas.')
    if registro.get('material_parede_externa_cadastrado') in NULOS or not registro.get('material_parede_externa_cadastrado'):
        motivos.append('Confirmar material das paredes externas.')
    if registro.get('endereco_cnpj_compativel') != 'SIM':
        motivos.append('Confirmar endereço e vínculo do estabelecimento.')
    if not regras['atividade_aceita_confirmada']:
        motivos.append('Confirmar aceitação da atividade/CNAE nas condições do produto.')
    if not regras['condicoes_contratuais_confirmadas']:
        motivos.append('Validar regras de contratação, interesse segurado e relação com o imóvel.')
    decisao = triagem(registro)
    motivos = decisao['motivos'] + motivos
    return {'elegivel': 'NAO' if decisao['bloqueado'] else 'PENDENTE' if motivos else 'SIM', 'motivos': motivos,
            'triagem': decisao,
            'observacao': 'Triagem preliminar. Plano sugerido não equivale a oferta ou aceitação contratual.'}


def recomendar_plano(pontuacoes, catalogo, config=None, registro=None):
    cfg = carregar_config(config)
    elegibilidade = verificar_elegibilidade(registro or {}, cfg)
    catalogo = adaptar_catalogo(catalogo)
    necessidades = MotorPontuacao(config=cfg).necessidades_plano(registro or {}, pontuacoes)
    conjuntos = {p: set(catalogo.loc[catalogo.plano.eq(p), 'cobertura_fixa']) for p in ORDEM_PLANOS}
    if not conjuntos['ESSENCIAL'] <= conjuntos['PRATICO'] <= conjuntos['TOTAL']:
        raise ValueError('Catálogo deve preservar a inclusão das coberturas dos planos anteriores.')
    if conjuntos['TOTAL'] != set(DECISORIAS)|set(COMUNS):
        raise ValueError('Catálogo e dez coberturas do motor divergem.')
    meta = cfg['planos']['meta_aderencia']
    indispensaveis = set(cfg['planos']['indispensaveis']) | set((registro or {}).get('coberturas_indispensaveis', []))
    criticas = {c for c in DECISORIAS if necessidades[c]['prioridade'] >= 70}
    indispensaveis |= criticas
    pesos = {c: cfg['coberturas'][c]['peso_plano'] for c in necessidades}
    foco = (registro or {}).get('prioridade_cliente')
    grupos = {'patrimonio': set(DECISORIAS) - {'RESPONSABILIDADE_CIVIL_EMPREGADOR'},
              'continuidade': {'DESPESAS_FIXAS', 'DANOS_ELETRICOS', 'PROTECAO_CIBERNETICA_AVALIAR', 'PERDA_PAGAMENTO_ALUGUEL'},
              'terceiros': {'RESPONSABILIDADE_CIVIL_ESTABELECIMENTO', 'RESPONSABILIDADE_CIVIL_EMPREGADOR'}}
    for c in grupos.get(foco, set()):
        pesos[c] *= 1.5
    total = sum(pesos[c]*s['prioridade'] for c,s in necessidades.items())
    if total <= 0:
        raise ValueError('Ao menos uma necessidade deve ter pontuação positiva.')
    comparacao = []
    anterior = 0.
    for plano in ORDEM_PLANOS:
        cobertas = conjuntos[plano]
        soma = lambda campo, codigos: sum(pesos[c]*necessidades[c][campo] for c in codigos)
        fora = set(necessidades)-cobertas
        atendidos = soma('prioridade', cobertas)
        aderencia = atendidos/total
        # Extremos da razão: cobertas baixas/descobertas altas e vice-versa.
        baixo, alto = soma('prioridade_min', cobertas), soma('prioridade_max', cobertas)
        baixo_fora, alto_fora = soma('prioridade_min', fora), soma('prioridade_max', fora)
        minimo = baixo/(baixo+alto_fora) if baixo+alto_fora else 1.
        maximo = alto/(alto+baixo_fora) if alto+baixo_fora else 1.
        faltantes = sorted(indispensaveis-cobertas)
        comparacao.append({'plano': plano, 'adequacao_relativa': aderencia,
            'aderencia_percentual': 100*aderencia,
            'aderencia_min_percentual': 100*minimo, 'aderencia_max_percentual': 100*maximo,
            'ganho_incremental': aderencia-anterior,
            'pontos_atendidos': atendidos, 'pontos_totais': total,
            'meta_percentual': meta, 'atinge_meta': 100*aderencia+1e-9 >= meta,
            'indispensaveis_ausentes': faltantes,
            'apto_simulacao': 100*aderencia+1e-9 >= meta and not faltantes,
            'coberturas_importantes_descobertas': sorted(c for c in fora if necessidades[c]['prioridade'] >= cfg['planos']['limiar_cobertura']),
            'coberturas_acrescentadas': sorted(cobertas-(conjuntos[ORDEM_PLANOS[ORDEM_PLANOS.index(plano)-1]] if plano != 'ESSENCIAL' else set())),
            'analise_preco': 'PENDENTE'})
        anterior = aderencia
    escolhido = next(p['plano'] for p in comparacao if p['apto_simulacao'])
    melhor = next(p['plano'] for p in comparacao if not p['indispensaveis_ausentes'] and p['aderencia_max_percentual']+1e-9 >= meta)
    robusto = next(p['plano'] for p in comparacao if not p['indispensaveis_ausentes'] and p['aderencia_min_percentual']+1e-9 >= meta)
    perguntas = list(elegibilidade['motivos']) + [
        'Confirmar caixa/reservas, valores de reposição e períodos de paralisação.',
        'Obter cotação, franquias, exclusões e limites contratuais.']
    for c,s in necessidades.items():
        s['peso'] = pesos[c]
        s['participacao_percentual'] = 100*pesos[c]*s['prioridade']/total
        s['indispensavel'] = c in indispensaveis
    aderencia = next(p['aderencia_percentual'] for p in comparacao if p['plano']==escolhido)
    return {'plano_recomendado': escolhido, 'indicacao_bloqueada': elegibilidade['elegivel'] == 'NAO',
        'coberturas_criticas': sorted(criticas), 'prioridade_cliente': foco or 'equilibrada', 'coberturas': sorted(conjuntos[escolhido]),
        'confianca_geral': sum(s['confianca']*pesos[c] for c,s in necessidades.items())/sum(pesos.values()),
        'elegibilidade': elegibilidade, 'comparacao': comparacao,
        'plano_cenario_inferior': melhor, 'plano_cenario_superior': robusto,
        'recomendacao_estavel': melhor == robusto, 'necessidades': necessidades,
        'meta_aderencia': meta, 'indispensaveis': sorted(indispensaveis),
        'justificativa': f'{escolhido} é o menor nível que alcança a meta de {meta:g}% e contém as coberturas indispensáveis. Aderência: {aderencia:.1f}% das dez necessidades ponderadas. Prioridades de 70 ou mais nos quatro índices exigem presença da cobertura para evitar diluição pela média. Preço e aceitação contratual pendentes; aderência não é probabilidade ou garantia de indenização.',
        'perguntas_confirmacao': perguntas, 'adicionais_para_avaliar': [],
        'observacao_triagem': 'Comparação técnica apenas; não recomendar contratação enquanto a triagem estiver bloqueada.' if elegibilidade['elegivel']=='NAO' else 'Indicação condicionada à aceitação oficial.'}
