"""Evidências do relatório local: campos permitidos, unidades e dados realmente usados."""
from __future__ import annotations

import hashlib
import json
from processamento import numero, caminho_referencia
from evidencias_origem import celulas_originais, confirmacao

# Campo -> rótulo, arquivo de origem, unidade. Nunca inclui endereço ou contato.
CAMPOS = {
    'bens_ponderados': ('Bens atribuídos à unidade', 'bens_cadastrados.csv', 'BRL'),
    'bens_total_referencia': ('Valor integral dos bens de referência', 'bens_cadastrados.csv', 'BRL'),
    'equipamentos_ponderados': ('Parcela de equipamentos elétricos nos bens', 'bens_cadastrados.csv', 'BRL'),
    'equipamentos_total_referencia': ('Equipamentos: valor integral de referência', 'bens_cadastrados.csv', 'BRL'),
    'informatica_ponderada': ('Bens de informática atribuídos à unidade', 'bens_cadastrados.csv', 'BRL'),
    'estoque_medio_estimado': ('Estoque médio estimado', 'sinais_financeiros_operacionais.csv', 'BRL'),
    'estoque_pico_estimado': ('Estoque de pico estimado', 'sinais_financeiros_operacionais.csv', 'BRL'),
    'valor_predio_reposicao_brl': ('Reconstrução do prédio, sem terreno', None, 'BRL'),
    'valor_vidros_reposicao_brl': ('Reposição de vidros declarada', None, 'BRL'),
    'folha_pagamento_mensal': ('Folha mensal da unidade', 'sinais_financeiros_operacionais.csv', 'BRL'),
    'despesa_fixa_mensal_estimada': ('Despesas fixas mensais estimadas', 'sinais_financeiros_operacionais.csv', 'BRL'),
    'valor_aluguel_recorrente': ('Aluguel mensal identificado', 'sinais_financeiros_operacionais.csv', 'BRL'),
    'pagamento_aluguel_recorrente': ('Sinal de pagamento recorrente de aluguel', 'sinais_financeiros_operacionais.csv', 'texto'),
    'faturamento_mensal': ('Faturamento mensal da empresa', 'empresas.csv', 'BRL'),
    'quantidade_unidades': ('Quantidade de unidades da empresa', 'enderecos_estabelecimentos.csv', 'numero'),
    'quantidade_funcionarios_estimada': ('Empregados estimados na empresa', 'empresas.csv', 'numero'),
    'funcionarios_unidade_confirmados': ('Empregados declarados nesta unidade', None, 'numero'),
    'dependencia_digital_pct': ('Dependência digital da empresa', 'empresas.csv', 'percentual'),
    'grupo_atividade': ('Grupo contextual da atividade', 'empresas.csv', 'texto'),
    'cnae_principal': ('CNAE utilizado', 'empresas.csv', 'texto'),
    'possui_termo_loja': ('Sinal cadastral de loja', 'enderecos_estabelecimentos.csv', 'texto'),
    'possui_termo_galeria': ('Sinal de galeria/shopping', 'enderecos_estabelecimentos.csv', 'texto'),
    'padrao_construtivo_cadastrado': ('Padrão construtivo cadastrado', 'enderecos_estabelecimentos.csv', 'texto'),
    'material_parede_externa_cadastrado': ('Material das paredes cadastrado', 'enderecos_estabelecimentos.csv', 'texto'),
    'possui_vidros_confirmado': ('Presença de vidros declarada', None, 'texto'),
    'possui_empregados_confirmado': ('Presença de empregados declarada', None, 'texto'),
}


def anexar_evidencias(record, indices, dimensoes, origens, base=None):
    vinculo = {'empresa_id': record.get('empresa_id'), 'imovel_id': record.get('imovel_id')}

    def campo(chave):
        label, arquivo, unidade = CAMPOS[chave]
        valor = record.get(chave)
        if unidade in ('BRL', 'numero', 'percentual'):
            valor = numero(valor)
        origem = origens.get(chave, 'Não informado')
        cadastral = origem == 'Cadastro BB/Datathon'
        if valor is None:
            estado, confirmar = 'AUSENTE', 'Não há valor disponível; solicitar confirmação.'
        elif 'excluído' in origem.lower():
            estado, confirmar = 'EXCLUIDO_ESCOPO', 'Valor zerado pelo escopo; não representa inexistência do bem.'
        elif origem.startswith('Mapa contextual'):
            estado, confirmar = 'HIPOTESE_MODELO', 'Mapeamento editorial do catálogo para o grupo do modelo; conferir correspondência com a operação.'
        elif origem.startswith('Estimativa do perfil agregado'):
            estado, confirmar = 'PERFIL_ATIVIDADE_ESTIMATIVA', 'Mediana da atividade; confirmar os valores reais desta empresa.'
        elif not cadastral:
            estado, confirmar = 'DECLARADO', 'Informação declarada no formulário; não equivale a vistoria ou documento verificado.'
        else:
            estado, confirmar = 'CADASTRO_ESTIMATIVA', 'Consta na base local do Datathon; confirmar existência, vínculo e valor atual de reposição.'
        campos_origem, transformacao = [chave], None
        if cadastral and arquivo=='bens_cadastrados.csv':
            campos_origem = ['valor_cadastrado']
            ponderado = chave not in ('bens_total_referencia', 'equipamentos_total_referencia')
            if ponderado:
                campos_origem.append('probabilidade_bem_no_imovel_referencia')
            if chave.startswith(('equipamentos','informatica')):
                campos_origem.append('tipo_bem')
            transformacao = 'Soma de valor_cadastrado × probabilidade_bem_no_imovel_referencia' if ponderado else 'Soma de valor_cadastrado dos bens de referência'
            if chave.startswith(('equipamentos','informatica')):
                transformacao += '; somente os tipos correspondentes, já incluídos no total dos bens'
        elif cadastral and chave=='quantidade_unidades':
            campos_origem = ['empresa_id', 'imovel_id']
            transformacao = 'Contagem de estabelecimentos da empresa, sem duplicar vínculos'
        orientacao = confirmacao(chave, estado)
        campos_fonte = campos_origem
        if arquivo == 'bens_cadastrados.csv':
            campos_fonte = ['valor_cadastrado']
            if chave not in ('bens_total_referencia', 'equipamentos_total_referencia'):
                campos_fonte.append('probabilidade_bem_no_imovel_referencia')
            if chave.startswith(('equipamentos', 'informatica')):
                campos_fonte.append('tipo_bem')
        elif chave == 'quantidade_unidades':
            campos_fonte = ['empresa_id', 'imovel_id']
        fontes = celulas_originais(base, record, chave, arquivo, campos_fonte, unidade)
        perfil = record.get('_perfil_cnae') if estado == 'PERFIL_ATIVIDADE_ESTIMATIVA' else None
        if perfil:
            agregado = {'bens_total_referencia': 'bens_ponderados',
                        'equipamentos_total_referencia': 'equipamentos_ponderados',
                        'estoque_pico_estimado': 'estoque_medio_estimado'}.get(chave, chave)
            perfil = dict(perfil, campo_agregado=agregado)
            if agregado != chave:
                transformacao = f'Reutiliza a mediana de {agregado}; não há observação independente de {chave}.'
                orientacao['significado'] = transformacao
        return {'campo': chave, 'rotulo': label, 'valor': valor, 'unidade': unidade, 'estado': estado,
                'campos_origem': campos_origem, 'transformacao_origem': transformacao,
                'origem': origem, 'arquivo': arquivo if cadastral and valor is not None else None,
                'chave': ({'empresa_id': record.get('empresa_id')} if arquivo=='empresas.csv' else vinculo) if cadastral else None,
                'sha256': base.hashes.get(arquivo) if base and cadastral else None,
                'fontes_originais': fontes, 'fonte_utilizada': cadastral and valor is not None,
                'perfil_referencia': perfil, 'significado': orientacao.pop('significado'),
                'confirmacao': orientacao, 'confirmar': confirmar}

    grupos = {
        'patrimonio': ['bens_ponderados','estoque_medio_estimado','bens_total_referencia','estoque_pico_estimado','valor_predio_reposicao_brl'],
        'roubavel': ['bens_ponderados','estoque_medio_estimado','bens_total_referencia','estoque_pico_estimado'],
        'equipamentos': ['equipamentos_ponderados','equipamentos_total_referencia','bens_ponderados'],
        'aluguel': ['pagamento_aluguel_recorrente','valor_aluguel_recorrente'],
        'despesas': ['despesa_fixa_mensal_estimada'],
        'digital': ['informatica_ponderada','despesa_fixa_mensal_estimada','dependencia_digital_pct'],
        'terceiros': ['grupo_atividade','possui_termo_loja','possui_termo_galeria'],
        'empregador': ['folha_pagamento_mensal','funcionarios_unidade_confirmados','quantidade_funcionarios_estimada','quantidade_unidades','possui_empregados_confirmado'],
        'vidros': ['valor_vidros_reposicao_brl','possui_vidros_confirmado','possui_termo_loja','possui_termo_galeria'],
    }
    from motor_pontuacao import carregar_config
    regras = carregar_config()['coberturas']
    for code, d in dimensoes.items():
        tipo = regras[code]['exposicao']
        d['evidencias'] = [campo(c) for c in grupos.get(tipo, grupos['vidros'])]
        d['dados_calculo'] = d['fator_impacto']['valor_original']

    def referencia(tipo, campos, nome_arquivo, modo):
        arquivo = caminho_referencia(nome_arquivo)
        if tipo == 'seguranca' and record.get('arquivo_seguranca'):
            from pathlib import Path
            arquivo = Path(record['arquivo_seguranca'])
            nome_arquivo = arquivo.name
        numericos = {'taxa_furto_domicilios','taxa_roubo_domicilios','exposicao_bruta','seguranca_da_cidade_0_1','confianca_seguranca_0_1',
            'roubo_comercio_total','estabelecimentos_referencia','taxa_por_mil_estabelecimentos','referencia_taxa_por_mil',
            'frequencia_rajada_forte','frequencia_rajada_severa','frequencia_vento_chuva','exposicao_climatica_bruta','exposicao_climatica_0_1',
            'dias_esperados','dias_vento_validos','dias_conjuntos_validos','grau_risco_nr4','pagina'}
        return {'tipo': tipo, 'fonte': record.get('fonte_' + tipo),
            'periodo': record.get('periodo_' + tipo, record.get('versao_' + tipo)),
            'granularidade': record.get('granularidade_' + tipo, 'CLASSE CNAE' if tipo=='nr4' else None),
            'modo_acesso': modo, 'consulta_ao_vivo': False,
            'arquivo': nome_arquivo, 'sha256_snapshot': (record.get('sha256_snapshot_seguranca') if tipo == 'seguranca' else None) or (hashlib.sha256(arquivo.read_bytes()).hexdigest() if arquivo.exists() else None),
            'metodologia': record.get('metodologia_' + tipo),
            'dados': {c: numero(record.get(c)) if c in numericos else record.get(c) for c in campos},
            'dados_originais': {c: record.get(c) for c in campos},
            'vinculo': {'codigo_ibge_municipio': record.get('codigo_ibge_municipio'),
                       'municipio': record.get('municipio_real'), 'uf': record.get('uf_real')} if tipo!='nr4' else
                      {'cnae': record.get('cnae_principal'), 'classe_cnae': record.get('classe_cnae')}}

    ssp = record.get('indicador_disponivel') in ('SIM','NAO') or numero(record.get('roubo_comercio_total')) is not None
    seguranca = referencia('seguranca', (['roubo_comercio_total','estabelecimentos_referencia','taxa_por_mil_estabelecimentos','referencia_taxa_por_mil','regioes_fonte','atualizado_em_utc','fonte_denominador','ano_denominador','meses_observados_seguranca','integridade_seguranca'] if ssp else
        ['taxa_furto_domicilios','taxa_roubo_domicilios','exposicao_bruta']) + ['seguranca_da_cidade_0_1','confianca_seguranca_0_1'],
        'seguranca_ssp.csv' if ssp else 'seguranca_municipal.csv',
        'Arquivo público SSP importado e normalizado localmente.' if ssp else 'Snapshot de tabelas públicas IBGE/SIDRA obtidas pelo preparador; não é consulta ao vivo.')
    clima = referencia('clima', ['frequencia_rajada_forte','frequencia_rajada_severa','frequencia_vento_chuva',
        'exposicao_climatica_bruta','exposicao_climatica_0_1','dias_esperados','dias_vento_validos','dias_conjuntos_validos',
        'modelo_clima','sha256_serie'], 'clima_municipal.csv', 'Snapshot calculado de séries da API histórica Open-Meteo/ERA5; não é previsão nem consulta ao vivo.')
    try:
        clima['parametros'] = json.loads(record.get('metodologia_clima') or '{}')
    except (ValueError, TypeError):
        clima['parametros'] = {}
    nr4 = referencia('nr4', ['grau_risco_nr4','descricao_nr4','pagina','sha256_documento'], 'nr4_cnae.csv',
        'Classificação extraída de documento oficial NR-4; não é API de acidentes ou de sinistros.')
    def reais(chave):
        n = numero(record.get(chave))
        return 'não informado' if n is None else 'R$ ' + f'{n:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')

    local = f"{record.get('municipio_real') or 'Município não informado'} / {record.get('uf_real') or 'UF não informada'}"
    q = record.get('questionario') or {}
    for code, s in indices.items():
        if code.startswith('ROUBO'):
            externa, contexto, chaves = seguranca, (
                'O indicador compara ocorrências de roubo em comércio com estabelecimentos de referência. Não mede o risco individual da unidade.' if ssp else
                'O território usa domicílios com vítimas no município, não roubos a esta empresa. O patrimônio e o estoque determinam o impacto; controles e bens transportáveis declarados ajustam a exposição quando há questionário.'), grupos['roubavel']
        elif code.startswith('VENDAVAL'):
            externa, contexto, chaves = clima, 'A série histórica municipal descreve frequência de vento e vento com chuva. Conteúdo, estoque e reconstrução disponível dimensionam o cenário. Padrão construtivo e respostas sobre telhado/exposição influenciam a vulnerabilidade; não há vistoria do telhado.', grupos['patrimonio'] + ['padrao_construtivo_cadastrado','material_parede_externa_cadastrado']
        elif code.endswith('EMPREGADOR'):
            externa, contexto, chaves = nr4, 'O CNAE vincula a unidade à classe e ao grau ocupacional da NR-4. Folha representa escala econômica, não indenização. Empregados da empresa não são distribuídos entre filiais sem confirmação local; tarefas declaradas complementam o contexto.', grupos['empregador'] + ['cnae_principal']
        else:
            externa, contexto, chaves = None, 'A presença e exposição de vidros vêm do questionário ou de sinais cadastrais fracos de loja/galeria. Não existe uma API externa de quebra de vidros integrada. Sem orçamento de reposição, o valor fica desconhecido; ausência declarada zera a prioridade.', grupos['vidros'] + ['grupo_atividade']
        if code.startswith('ROUBO'):
            leitura = f"Nesta unidade em {local}, os bens atribuídos são {reais('bens_ponderados')} e o estoque médio é {reais('estoque_medio_estimado')}. Reconstrução do prédio não entra no cenário de subtração do conteúdo. "
            if 'securityControls' in q:
                leitura += ('Foram declarados alarme monitorado e controle de acesso. ' if q['securityControls'] else 'Não foram declarados alarme monitorado e controle de acesso em funcionamento. ')
                leitura += ('Há bens declarados de fácil transporte e revenda. ' if q['portableGoods'] else 'Não há bens declarados de fácil transporte e revenda. ')
            else:
                leitura += 'Controles de acesso e portabilidade dos bens ainda não foram confirmados. '
            if record.get('escopo_protecao') == 'building':
                leitura += 'O escopo protege somente o prédio: a prioridade de roubo do conteúdo foi zerada. '
        elif code.startswith('VENDAVAL'):
            leitura = f"Em {local}, o cenário patrimonial considera bens {reais('bens_ponderados')}, estoque médio {reais('estoque_medio_estimado')} e reconstrução {reais('valor_predio_reposicao_brl')}. "
            leitura += f"O padrão construtivo cadastrado é {record.get('padrao_construtivo_cadastrado') or 'desconhecido'}. "
            if 'roofMaintained' in q:
                leitura += ('O telhado foi declarado inspecionado e conservado. ' if q['roofMaintained'] else 'A inspeção e a conservação do telhado não foram confirmadas. ')
                leitura += ('Há bens externos declarados expostos ao vento. ' if q['exposedAssets'] else 'Não foram declarados bens externos expostos ao vento. ')
            else:
                leitura += 'Manutenção do telhado e exposição externa ainda não foram respondidas. '
        elif code.endswith('EMPREGADOR'):
            leitura = f"O CNAE utilizado é {record.get('cnae_principal') or 'desconhecido'}, com grau NR-4 {record.get('grau_risco_nr4') or 'não localizado'}. A folha mensal desta unidade é {reais('folha_pagamento_mensal')}. "
            if q.get('hasEmployees') is False:
                leitura += 'Você declarou que não há empregados nesta unidade; a prioridade foi zerada. '
            elif q.get('hasEmployees') is True:
                leitura += ('Há empregados com tarefas declaradas de exposição física. ' if q.get('hazardousWork') else 'Há empregados, sem as tarefas de exposição física descritas no questionário. ')
            else:
                leitura += 'A presença de empregados nesta unidade ainda precisa de confirmação. '
            if numero(record.get('quantidade_unidades')) != 1 and numero(record.get('funcionarios_unidade_confirmados')) is None:
                leitura += 'O número empresarial de empregados não foi distribuído entre as unidades. '
        else:
            leitura = f"A reposição de vidros informada para esta unidade é {reais('valor_vidros_reposicao_brl')}. "
            if q.get('hasGlass') is False or record.get('possui_vidros_confirmado') == 'NAO':
                leitura += 'Foi declarada ausência de vidros a proteger; a prioridade foi zerada. '
            elif q.get('hasGlass') is True:
                leitura += ('Há vidros declarados expostos à rua, circulação ou impactos. ' if q.get('glassExposed') else 'Há vidros declarados, sem a exposição a impactos descrita no questionário. ')
            else:
                leitura += f"Sem confirmação de vidros, foram usados os sinais cadastrais de loja ({record.get('possui_termo_loja') or 'desconhecido'}) e galeria ({record.get('possui_termo_galeria') or 'desconhecido'}). Esses sinais não comprovam vidraças. "
        s['leitura_contextual'] = leitura
        s['explicacao_contextual'] = contexto
        s['evidencias'] = [campo(c) for c in dict.fromkeys(chaves + ['despesa_fixa_mensal_estimada','faturamento_mensal','quantidade_unidades'])]
        if externa is not None:
            externa = dict(externa)
            tipo = externa['tipo']
            disponivel = (numero(record.get('grau_risco_nr4')) in (1,2,3,4) if tipo=='nr4' else
                numero(record.get('seguranca_da_cidade_0_1' if tipo=='seguranca' else 'exposicao_climatica_0_1')) is not None and
                numero(record.get('seguranca_da_cidade_0_1' if tipo=='seguranca' else 'exposicao_climatica_0_1')) <= 1 and
                (numero(record.get('confianca_'+tipo+'_0_1', record.get('confianca_territorial_0_1'))) or 0) > 0)
            externa['disponivel'] = disponivel
            externa['condicao'] = 'Referência presente; conferir nos fatores a contribuição efetiva e eventuais exclusões de exposição.' if disponivel else 'Referência ausente ou sem confiança utilizável. O componente desconhecido mantém incerteza explícita; não foi criada uma taxa externa.'
            if tipo == 'seguranca':
                qualidade = s['qualidade_seguranca']
                externa['disponivel'] = qualidade['utilizavel']
                externa['qualidade'] = qualidade
                externa['condicao'] = ' '.join(qualidade['motivos'])
                if not qualidade['utilizavel']:
                    contexto = 'Referência territorial excluída: ' + externa['condicao'] + ' A prioridade restante usa cenário e informações empresariais, sem criminalidade territorial validada.'
                    s['explicacao_contextual'] = contexto
        s['referencia_publica'] = externa
        s['respostas_utilizadas'] = {k: (record.get('questionario') or {}).get(k) for k in
            ({'ROUBO_FURTO_ARROMBAMENTO':['securityControls','portableGoods'], 'VENDAVAL_EVENTOS_CORRELATOS':['roofMaintained','exposedAssets'],
              'RESPONSABILIDADE_CIVIL_EMPREGADOR':['hasEmployees','hazardousWork'], 'QUEBRA_DE_VIDROS':['hasGlass','glassExposed']}[code])}

    bens = []
    if base is not None and base.bens is not None:
        linhas = base.bens.loc[base.bens.empresa_id.eq(record.get('empresa_id')) & base.bens.imovel_id_referencia.eq(record.get('imovel_id'))]
        for r in linhas.to_dict('records'):
            valor, prob = numero(r.get('valor_cadastrado')), numero(r.get('probabilidade_bem_no_imovel_referencia'))
            bens.append({'bem_id': r['bem_id'], 'tipo_bem': r.get('tipo_bem'), 'valor_cadastrado': valor,
                'probabilidade_vinculo': prob, 'valor_ponderado': valor*prob if valor is not None and prob is not None and prob<=1 else None,
                'confianca_vinculo': r.get('nivel_confianca_vinculo')})
    return {'vinculo': vinculo, 'bens': bens, 'arquivo_bens': 'bens_cadastrados.csv',
        'sha256_bens': base.hashes.get('bens_cadastrados.csv') if base else None,
        'bens_cadastrais_utilizados': origens.get('bens_ponderados') == 'Cadastro BB/Datathon' and numero(record.get('bens_ponderados')) is not None,
        'formula_bens': 'Soma de valor_cadastrado × probabilidade_bem_no_imovel_referencia, uma única vez por bem; equipamentos já são subconjunto dos bens.',
        'observacao': 'Dados efetivos da base local do Datathon e declarações da simulação. Não representam consulta bancária de produção. Ausências e estimativas são preservadas.'}
