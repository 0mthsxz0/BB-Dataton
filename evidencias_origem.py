"""Células permitidas e pendências de validação, sem expor outras empresas."""
from processamento import TIPOS_ELETRICOS, numero

# Significado, o que confirmar e onde obter a confirmação.
GUIA = {
    'bens_ponderados': ('Soma do valor de cada bem multiplicado pelo peso estimado de vínculo com esta unidade. Não é valor de indenização.', 'Existência dos bens nesta unidade, vínculo e custo atual de reposição, sem duplicar estoque.', 'Inventário por unidade, notas fiscais e orçamentos atuais dos fornecedores.'),
    'bens_total_referencia': ('Soma integral dos bens de referência, antes da ponderação do vínculo.', 'Quais bens pertencem de fato à unidade e seus valores atuais, sem duplicar estoque.', 'Inventário patrimonial por unidade, notas fiscais e orçamentos de reposição.'),
    'equipamentos_ponderados': ('Parcela dos bens de categorias elétricas, ponderada pelo vínculo. Já integra o total dos bens.', 'Relação, localização e custo de reposição dos equipamentos elétricos.', 'Inventário de equipamentos por unidade, notas fiscais e fornecedores.'),
    'equipamentos_total_referencia': ('Valor integral dos equipamentos elétricos de referência, antes da ponderação; já integra os bens.', 'Vínculo local e reposição dos equipamentos, sem somá-los novamente aos bens.', 'Inventário de equipamentos por unidade e orçamentos de reposição.'),
    'informatica_ponderada': ('Parcela dos bens de informática ponderada pelo vínculo; já integra o total dos bens.', 'Equipamentos de informática presentes e seu custo atual de reposição.', 'Inventário de informática, notas fiscais e fornecedores.'),
    'estoque_medio_estimado': ('Estimativa do valor normalmente mantido em estoque nesta unidade.', 'Estoque médio local, período de referência e ausência de duplicidade com os bens.', 'Controle de estoque, balanço de inventário e registros de compras da unidade.'),
    'estoque_pico_estimado': ('Estimativa do maior estoque em períodos de maior movimento.', 'Maior estoque local e sazonalidade do período coberto.', 'Histórico mensal de estoque, inventários sazonais e planejamento de compras.'),
    'valor_predio_reposicao_brl': ('Custo para reconstruir a edificação, sem incluir o terreno.', 'Área, padrão construtivo, custo atual de reconstrução e interesse a segurar.', 'Planta, memorial descritivo e orçamento de engenheiro ou construtora; confirmar com o proprietário.'),
    'valor_vidros_reposicao_brl': ('Custo para repor os vidros e espelhos a proteger; quantidade sozinha não determina esse custo.', 'Medidas, tipo de vidro, instalação e orçamento de reposição.', 'Levantamento no local e orçamento de vidraçaria com instalação.'),
    'folha_pagamento_mensal': ('Folha mensal atribuída ao estabelecimento; não representa indenização trabalhista.', 'Valor atual da folha e quais empregados trabalham nesta unidade.', 'Folha de pagamento por lotação, departamento pessoal e contador.'),
    'despesa_fixa_mensal_estimada': ('Estimativa mensal das despesas que continuam mesmo se a operação parar.', 'Despesas efetivamente mantidas durante a paralisação e período necessário de proteção.', 'Demonstração do resultado, razão contábil, contratos e contador da unidade.'),
    'valor_aluguel_recorrente': ('Valor mensal de aluguel identificado; não comprova propriedade ou obrigação contratual.', 'Aluguel vigente, relação com o imóvel e obrigação em caso de paralisação.', 'Contrato de locação, aditivos e comprovantes de pagamento.'),
    'pagamento_aluguel_recorrente': ('Sinal de pagamentos recorrentes de aluguel; não substitui contrato de locação.', 'Se há aluguel e obrigação contratual vigente nesta unidade.', 'Contrato de locação, aditivos e comprovantes de pagamento.'),
    'faturamento_mensal': ('Receita mensal da empresa inteira; não é lucro nem receita de uma filial específica.', 'Período, receita atual e separação por unidade quando houver filiais.', 'Relatórios de vendas, documentos fiscais e contador; solicitar demonstrativo por estabelecimento.'),
    'quantidade_unidades': ('Contagem dos estabelecimentos cadastrados para a empresa; não distribui receita ou empregados entre filiais.', 'Lista atual das unidades em funcionamento.', 'Cadastro de matriz e filiais e relação de estabelecimentos com o responsável da empresa.'),
    'quantidade_funcionarios_estimada': ('Estimativa de empregados na empresa inteira; não é o efetivo confirmado desta unidade.', 'Quantidade de empregados efetivamente lotados nesta unidade.', 'Departamento pessoal, folha por lotação e responsável pelo estabelecimento.'),
    'funcionarios_unidade_confirmados': ('Quantidade declarada de empregados que trabalham neste estabelecimento.', 'Quantidade atual e lotação dos empregados.', 'Departamento pessoal e folha de pagamento por estabelecimento.'),
    'dependencia_digital_pct': ('Parcela estimada da operação dependente de recursos digitais; não é chance de ataque.', 'Sistemas essenciais, dependência real e capacidade de operar sem eles.', 'Responsável pela operação, equipe de tecnologia e plano de continuidade.'),
    'grupo_atividade': ('Grupo usado pelo modelo para contextualizar a atividade; não confirma o enquadramento do seguro.', 'Atividade realmente exercida e correspondência com a categoria do produto.', 'Responsável pela empresa, descrição operacional e catálogo de atividades do produto.'),
    'cnae_principal': ('Código da atividade econômica; não identifica uma empresa de forma única.', 'Código atual e atividade efetivamente exercida no estabelecimento.', 'Comprovante de inscrição da empresa e contador.'),
    'possui_termo_loja': ('Sinal textual de loja no cadastro; não comprova existência de vidros ou circulação de clientes.', 'Uso real do espaço, atendimento ao público e presença de vidros.', 'Responsável pelo estabelecimento, fotos atuais ou vistoria.'),
    'possui_termo_galeria': ('Sinal textual de galeria ou shopping; não comprova proteção física ou desconto.', 'Se o espaço fica em shopping, prédio comercial ou galeria e quais controles existem.', 'Responsável pelo local, administração do condomínio e vistoria.'),
    'padrao_construtivo_cadastrado': ('Categoria construtiva do cadastro; não confirma conservação do telhado.', 'Características reais e estado de conservação da construção.', 'Memorial descritivo, responsável pelo imóvel e vistoria técnica.'),
    'material_parede_externa_cadastrado': ('Material predominante das paredes externas informado no cadastro.', 'Material real e eventual presença de componentes combustíveis.', 'Memorial descritivo, fotos e vistoria do imóvel.'),
    'possui_vidros_confirmado': ('Declaração de presença ou ausência de vidros a proteger.', 'Presença, tipo e exposição dos vidros, além do custo para reposição.', 'Responsável pelo estabelecimento, levantamento local e vidraçaria.'),
    'possui_empregados_confirmado': ('Declaração sobre empregados trabalhando nesta unidade.', 'Lotação local e tarefas com exposição física.', 'Responsável pela unidade, departamento pessoal e descrição das funções.'),
}
CELULAS = {
    'valor_cadastrado': ('BRL', 'Valor registrado para este bem, antes de aplicar o peso de vínculo; pode precisar de atualização.'),
    'probabilidade_bem_no_imovel_referencia': ('proporcao', 'Peso estimado de vínculo do bem com a unidade: 100% considera todo o valor; 50% considera metade. Não é chance de sinistro.'),
    'tipo_bem': ('texto', 'Categoria usada para separar os equipamentos e a informática dentro dos bens.'),
    'empresa_id': ('texto', 'Identificador da empresa na base local do Datathon.'),
    'imovel_id': ('texto', 'Identificador do estabelecimento na base local do Datathon.'),
}


def celulas_originais(base, record, chave, arquivo, campos, unidade):
    """Retorna só colunas permitidas, na ordem original e com a grafia da célula."""
    tabela = (getattr(base, 'fontes', None) or {}).get(arquivo)
    if tabela is None:
        return []
    linhas = tabela.loc[tabela.empresa_id.eq(record.get('empresa_id'))]
    if arquivo == 'bens_cadastrados.csv':
        linhas = linhas.loc[linhas.imovel_id_referencia.eq(record.get('imovel_id'))]
        if chave.startswith('equipamentos'):
            linhas = linhas.loc[linhas.tipo_bem.isin(TIPOS_ELETRICOS)]
        elif chave == 'informatica_ponderada':
            linhas = linhas.loc[linhas.tipo_bem.eq('EQUIPAMENTO_INFORMATICA')]
    elif arquivo != 'empresas.csv' and chave != 'quantidade_unidades':
        linhas = linhas.loc[linhas.imovel_id.eq(record.get('imovel_id'))]
    saida = []
    duplicados = linhas.duplicated() if arquivo == 'bens_cadastrados.csv' else None
    for indice, row in linhas.iterrows():
        celulas = []
        for c in campos:
            if c not in tabela.columns:
                continue
            u, significado = CELULAS.get(c, (unidade, GUIA[chave][0]))
            celulas.append({'campo': c, 'valor_original': row[c], 'unidade': u, 'significado': significado})
        if celulas:
            observacao = None
            if arquivo == 'bens_cadastrados.csv':
                ponderado = chave not in ('bens_total_referencia', 'equipamentos_total_referencia')
                prob = numero(row.get('probabilidade_bem_no_imovel_referencia'))
                if duplicados.loc[indice]:
                    observacao = 'Registro duplicado no arquivo; não é somado novamente.'
                elif numero(row.get('valor_cadastrado')) is None:
                    observacao = 'Valor cadastrado inválido ou ausente; este registro não entra na soma.'
                elif ponderado and (prob is None or prob > 1):
                    observacao = 'Peso de vínculo inválido ou ausente; este registro não entra na soma ponderada.'
            saida.append({'arquivo': arquivo, 'linha_tabela': int(indice) + 2,
                          'registro': row.get('bem_id') or row.get('imovel_id') or row.get('empresa_id'),
                          'observacao': observacao, 'celulas': celulas})
    return saida


def confirmacao(chave, estado):
    significado, pendencia, local = GUIA[chave]
    motivos = {
        'AUSENTE': 'O dado necessário não foi informado ou o valor disponível não é válido para o cálculo.',
        'CADASTRO_ESTIMATIVA': 'O cadastro é uma referência estimada; não comprova a situação atual deste estabelecimento.',
        'PERFIL_ATIVIDADE_ESTIMATIVA': 'O valor é a mediana de outras empresas da mesma atividade; não foi medido nesta empresa.',
        'DECLARADO': 'A informação foi declarada, mas a documentação e a situação no local ainda não foram verificadas.',
        'HIPOTESE_MODELO': 'O grupo foi atribuído por uma regra contextual; a correspondência com a operação real não está confirmada.',
        'EXCLUIDO_ESCOPO': 'O valor foi zerado porque este item está fora do escopo escolhido; isso não significa ausência física.',
    }
    return {'significado': significado, 'motivo': motivos[estado],
            'pendencias': [pendencia] if estado != 'EXCLUIDO_ESCOPO' else [],
            'onde_encontrar': local if estado != 'EXCLUIDO_ESCOPO' else 'Revise a escolha entre imóvel, conteúdo ou ambos se desejar incluir este item.'}
