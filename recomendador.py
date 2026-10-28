"""Seleção de planos por adequação incremental e elegibilidade preliminar."""
from __future__ import annotations

from motor_pontuacao import DECISORIAS, COMUNS, carregar_config
from processamento import NULOS

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
    return {'elegivel': 'PENDENTE' if motivos else 'SIM', 'motivos': motivos,
            'observacao': 'Triagem preliminar. Plano sugerido não equivale a oferta ou aceitação contratual.'}


def recomendar_plano(pontuacoes, catalogo, config=None, registro=None):
    cfg = carregar_config(config)
    fixas = {c: pontuacoes[c] for c in DECISORIAS}
    conjuntos = {p: set(catalogo.loc[catalogo.plano.eq(p), 'cobertura_fixa']) for p in ORDEM_PLANOS}
    if any(conjuntos[p] - (set(DECISORIAS)|set(COMUNS)) for p in ORDEM_PLANOS):
        raise ValueError('Catálogo contém cobertura sem modelo de análise.')
    if not conjuntos['ESSENCIAL'] <= conjuntos['PRATICO'] <= conjuntos['TOTAL']:
        raise ValueError('Catálogo deve preservar a inclusão das coberturas dos planos anteriores.')
    if conjuntos['TOTAL'] != set(DECISORIAS)|set(COMUNS):
        raise ValueError('Catálogo e nove coberturas do motor divergem.')
    limites = cfg['planos']
    pesos = {c: cfg['coberturas'][c]['peso_plano'] for c in fixas}

    def escolher(campo):
        necessidades = {c: fixas[c][campo] / 100 for c in fixas}
        total = sum(pesos[c] * n for c, n in necessidades.items()) or 1
        escolhido = 'ESSENCIAL'
        for candidato in ORDEM_PLANOS[1:]:
            novas = (conjuntos[candidato] - conjuntos[escolhido]) & set(fixas)
            ganho = sum(pesos[c] * necessidades[c] for c in novas) / total
            relevantes = [c for c in novas if necessidades[c] * 100 >= limites['limiar_cobertura']]
            criticas = [c for c in novas if necessidades[c] * 100 >= limites['limiar_critico']]
            if criticas or (relevantes and ganho >= limites['ganho_incremental_minimo']):
                escolhido = candidato
        return escolhido

    escolhido = escolher('prioridade')
    comparacao = []
    total = sum(pesos[c] * s['prioridade'] for c, s in fixas.items()) or 1
    anterior = set()
    for plano in ORDEM_PLANOS:
        cobertas = conjuntos[plano]
        descobertas = [c for c, s in fixas.items() if c not in cobertas and s['prioridade'] >= limites['limiar_cobertura']]
        novas = (cobertas - anterior) & set(fixas)
        comparacao.append({'plano': plano,
            'adequacao_relativa': sum(pesos[c] * fixas[c]['prioridade'] for c in cobertas & set(fixas)) / total,
            'ganho_incremental': sum(pesos[c] * fixas[c]['prioridade'] for c in novas) / total,
            'coberturas_importantes_descobertas': descobertas,
            'coberturas_acrescentadas': sorted(novas), 'analise_preco': 'PENDENTE'})
        anterior = cobertas
    criticas = [c for c in conjuntos[escolhido] - conjuntos['ESSENCIAL']
                if fixas[c]['prioridade'] >= limites['limiar_cobertura']]
    motivo = ('Essencial atende ao critério configurado de adequação; coberturas comuns não geram upgrade.'
              if escolhido == 'ESSENCIAL' else
              f'{escolhido} acrescenta proteção relevante: ' + ', '.join(fixas[c]['nome'] for c in sorted(criticas)) + '.')
    inferior, superior = escolher('prioridade_min'), escolher('prioridade_max')
    elegibilidade = verificar_elegibilidade(registro or {}, cfg)
    perguntas = list(elegibilidade['motivos'])
    perguntas += ['Confirmar caixa/reservas, valores de reposição e períodos de paralisação.',
                  'Obter cotação, franquias, exclusões e limites contratuais.']
    return {'plano_recomendado': escolhido, 'coberturas': sorted(conjuntos[escolhido]),
        'confianca_geral': sum(s['confianca'] for s in fixas.values()) / len(fixas),
        'elegibilidade': elegibilidade, 'comparacao': comparacao,
        'plano_cenario_inferior': inferior, 'plano_cenario_superior': superior,
        'recomendacao_estavel': inferior == superior,
        'justificativa': motivo + ' Adequação relativa; preço e aceitação contratual pendentes.',
        'perguntas_confirmacao': perguntas,
        'adicionais_para_avaliar': []}
