"""Política versionada do desafio; não reproduz subscrição ou tarifas da seguradora."""
from __future__ import annotations

import json
from pathlib import Path

REGRAS = json.loads((Path(__file__).parent / 'frontend/public/product-rules.json').read_text(encoding='utf-8'))
CIBER = 'PROTECAO_CIBERNETICA_AVALIAR'


def adaptar_catalogo(catalogo):
    """Conserva o CSV de origem e acrescenta a sexta comum exigida pelo guia."""
    import pandas as pd
    copia = catalogo.copy()
    faltantes = [{'plano': p, 'cobertura_fixa': CIBER} for p in REGRAS['plans']
                 if not ((copia.plano == p) & (copia.cobertura_fixa == CIBER)).any()]
    return pd.concat([copia, pd.DataFrame(faltantes)], ignore_index=True) if faltantes else copia


def triagem(registro):
    from processamento import numero
    motivos, bloqueios = [], []
    estado = registro.get('situacao_imovel_cadastral')
    if estado in ('EM_OBRA', 'CONDENADO', 'EM_RECONSTRUCAO'):
        bloqueios.append('Situação do imóvel incompatível com a triagem do guia: ' + estado + '.')
    material = registro.get('material_parede_externa_cadastrado')
    if material in ('MADEIRA', 'MATERIAL_COMBUSTIVEL'):
        bloqueios.append('Parede externa combustível: encaminhar para análise oficial de aceitação.')
    valores = [numero(registro.get(c)) for c in ('bens_ponderados', 'estoque_medio_estimado', 'valor_predio_reposicao_brl')]
    objeto = sum(v for v in valores if v is not None) if any(v is not None for v in valores) else None
    acima = objeto is not None and objeto > REGRAS['basicLimitBRL']
    if acima:
        bloqueios.append('Objeto básico estimado acima de R$ 7,5 milhões: avaliar Seguro Personalizado Empresarial.')
    if registro.get('escopo_protecao') in ('building', 'both') and numero(registro.get('valor_predio_reposicao_brl')) is None:
        motivos.append('Confirmar reconstrução sem terreno para completar o limite único de prédio/conteúdo.')
    return {'bloqueado': bool(bloqueios), 'encaminhamento': 'PERSONALIZADO' if acima else 'ANALISE_OFICIAL' if bloqueios else None,
            'motivos': bloqueios + motivos, 'valor_objeto_basico_brl': objeto, 'limite_basico_brl': REGRAS['basicLimitBRL'],
            'objeto_completo': all(v is not None for v in valores),
            'observacao': 'Limite único de prédio/conteúdo; não soma limites de aluguel, RC ou outras coberturas.'}


def personalizar(registro, recomendacao, dimensoes):
    from processamento import numero
    from opcionais import avaliar_opcionais, comparar_alternativas
    operacao = registro.get('operacao_confirmada', {})
    adicionais = avaliar_opcionais(registro, REGRAS)
    # Confirmed relevant protections compose the proposal, never an issued contract.
    automaticos = {x['code'] for x in adicionais if x['confirmacao'] is True and x['operation'] != 'interruption'}
    recusados = set(registro.get('adicionais_recusados', []))
    escolhido = registro.get('plano_escolhido')
    selecionado = escolhido or recomendacao['plano_recomendado']
    if not escolhido:
        ordem = list(REGRAS['plans'])
        selecionado = next(p for p in ordem[ordem.index(selecionado):]
            if all(p in x['plans'] for x in adicionais if x['code'] in automaticos - recusados))

    padrao = set(REGRAS['plans'][selecionado])
    ajustes = registro.get('ajustes_coberturas', {})
    pacote = (padrao | set(ajustes.get('include', []))) - set(ajustes.get('exclude', []))
    if not set(REGRAS['mandatory']) <= pacote:
        raise ValueError('As seis coberturas obrigatórias não podem ser excluídas.')
    if set(registro.get('coberturas_indispensaveis', [])) - pacote:
        raise ValueError('O pacote escolhido não contém todas as coberturas que você considerou indispensáveis. Inclua a cobertura ou escolha outro plano.')
    automaticos = {x['code'] for x in adicionais if x['code'] in automaticos and selecionado in x['plans']}
    pedidos = (set(registro.get('adicionais_escolhidos', [])) | automaticos) - recusados
    validos = {x['code'] for x in adicionais}
    if (pedidos | recusados) - validos:
        raise ValueError('Adicional desconhecido.')
    if len([c for c in pedidos if c.startswith('LUCRO_')]) > 1:
        raise ValueError('Escolha apenas uma modalidade de lucro; confirme a DRE e as condições com o especialista.')
    for extra in adicionais:
        extra['solicitada'] = extra['code'] in pedidos
        extra['incluida_automaticamente'] = extra['code'] in automaticos and extra['code'] not in recusados
        extra['permitida_no_plano'] = selecionado in extra['plans']
        if extra['solicitada'] and (not extra['permitida_no_plano'] or extra.get('operation') and extra['confirmacao'] is not True):
            raise ValueError('Adicional exige plano compatível e confirmação da operação: ' + extra['name'])
    protecoes = sorted(pacote | pedidos)
    nomes = {**{c:n['nome'] for c,n in recomendacao['necessidades'].items()}, **{x['code']:x['name'] for x in adicionais}}
    necessidades = recomendacao['necessidades']
    total = sum(n['peso'] * n['prioridade'] for n in necessidades.values())
    pontos = sum(n['peso'] * n['prioridade'] for c, n in necessidades.items() if c in pacote)
    lacunas = [n['nome'] for c, n in necessidades.items() if c not in pacote and (n['indispensavel'] or n['prioridade'] >= 70)]
    return {'versaoRegras': REGRAS['version'], 'fontesRegras': REGRAS['sources'], 'conciliacao': REGRAS['reconciliation'],
        'triagem': triagem(registro), 'adicionais': adicionais,
        'alternativas': comparar_alternativas(recomendacao, adicionais),
        'pacote': {'plano': selecionado, 'coberturas_totais': protecoes,
            'protecoes': [{'codigo':c,'nome':nomes[c]} for c in protecoes], 'quantidade_coberturas':len(protecoes), 'coberturas': sorted(pacote), 'obrigatorias': REGRAS['mandatory'],
            'adicionais_condicionais': sorted(pedidos), 'vigencia_anos': registro.get('vigencia_anos', 1),
            'aderencia_percentual': 100 * pontos / total, 'lacunas_prioritarias': lacunas,
            'alteracoes': {'incluidas': sorted(pacote - padrao), 'excluidas': sorted(padrao - pacote)},
            'observacao': 'Composição de simulação. Adicionais solicitados dependem de atividade, limites e aceitação; não participam da aderência das dez necessidades.'},
        'shopping': {'requisitos_confirmados': operacao.get('shoppingControls'),
            'mensagem': 'Prédio comercial ou galeria protegida: condições de segurança e eventual desconto dependem de avaliação oficial; nenhum desconto presumido.' if registro.get('tipo_local_funcionamento_declarado') in ('building', 'gallery') else 'Possível enquadramento para desconto, sujeito à cotação oficial; nenhum percentual foi aplicado.' if operacao.get('shoppingControls') else 'Shopping exige confirmação de segurança própria, brigada, hidrantes e sprinklers. Nenhum desconto presumido.'},
        'assistencias': {'personalizaveis': False, 'mensagem': 'Pacote fixo do plano. Assistência Proteção Digital não substitui cobertura cibernética.'},
        'contexto_confirmado': {'operacao': operacao, 'relacao_imovel': registro.get('relacao_imovel_confirmada'),
            'situacao_imovel': registro.get('situacao_imovel_cadastral'),
            'material_parede': registro.get('material_parede_externa_cadastrado')}}
