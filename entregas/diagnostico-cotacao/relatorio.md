# Diagnóstico de elegibilidade e informações mínimas de cotação

Base: **2978 estabelecimentos de 2500 empresas**, desenvolvimento. Data: 28/10/2026.
Fonte normativa do desafio: Guia_Times_Datathon_Protecao_Inteligente_Final.pdf, seção 10.1, p. 13; seção 10.2, pp. 14–15 para planos. Dados: empresas, endereços, sinais financeiros, bens, território e dicionário dos CSVs locais. Não inclui respostas de sessões do navegador nem verificação oficial da seguradora.

## Resultado sem dupla contagem

- **78 unidades (2,62%)** com impedimento explícito cadastrado: em obra.
- **2900 unidades (97,38%)** sem impedimento explícito identificado, com verificações mínimas pendentes.
- **Zero unidades demonstradamente prontas para cotação completa apenas pelos CSVs**: o pacote anonimizado não contém identificação legal e confirmações contratuais/operacionais. Isso não é uma taxa de rejeição real.
- Entre os impedimentos identificados, **obra representa 100% dos casos**. Os critérios sem informação não entram nessa composição: zero identificado não significa zero existente.

## Metodologia dos percentuais

Percentual = unidades com o motivo / 2978 × 100. No resultado geral o impedimento tem precedência; nas tabelas por motivo uma unidade pode aparecer em várias linhas, por isso os percentuais não devem ser somados. O denominador de cada linha é a base inteira, inclusive imóveis em obra. Ausência, estimativa sem confirmação e dado incompatível são apresentados separadamente de impedimento.

## Todos os critérios de inelegibilidade e encaminhamento

| Motivo / parâmetro | Unidades | % da base | Regra e interpretação |
|---|---:|---:|---|
| Atividade rural: sinal pelo CNAE | 0 | 0,00% | Divisões CNAE 01, 02 ou 03. Nenhum sinal rural nos CNAEs fornecidos; confirmar atividade efetiva e aceitação. |
| Localização rural ou nas áreas restritas do guia | 0 | 0,00% | Confirmação específica da localização. Não verificável em 100%: sem campo próprio. Não inferir de renda, bairro, CEP ou coordenadas perturbadas. Zero identificado não prova ausência. |
| Imóvel tombado ou desapropriado | 0 | 0,00% | Confirmação documental específica. Não verificável em 100%: sem campos próprios. |
| Imóvel condenado | 0 | 0,00% | situacao_imovel_cadastral = CONDENADO. Nenhum registro com esse valor. IRREGULAR não equivale a condenado. |
| Construção, reforma ou reconstrução | 78 | 2,62% | Situação em obra/construção/reforma/reconstrução. EM_OBRA é o único impedimento explícito encontrado. Confirmar situação atual antes de decisão oficial. |
| Paredes externas combustíveis | 0 | 0,00% | Material = MADEIRA ou MATERIAL_COMBUSTIVEL. Nenhum positivo informado; em 2.524 unidades o material é desconhecido. |
| Mesmo objeto em outra proposta BB Seguros | 0 | 0,00% | Checar objeto, proposta/apólice existente. Não verificável em 100%: sem histórico de propostas por objeto. |
| Objeto básico acima de R$ 7,5 milhões | 0 | 0,00% | Prédio e conteúdo, limite único > 7.500.000. Encaminhar ao Personalizado; não é recusa geral. Nenhum subtotal disponível supera o corte, mas falta reconstrução em 100%. Não comprova valor total abaixo do limite. |

## Lacunas de informação e confirmação; motivos de revisão

| Motivo / parâmetro | Unidades | % da base | Regra e interpretação |
|---|---:|---:|---|
| Identificação legal: nome/razão social e CPF/CNPJ | 2978 | 100,00% | Identificação legal válida; IDs anônimos não substituem CPF/CNPJ. Ausência estrutural do pacote anonimizado, não falha do cliente real. |
| Relação com o imóvel | 2978 | 100,00% | Confirmar proprietário ou inquilino. Pagamento de aluguel ou sua ausência não comprova a relação jurídica. |
| Escopo: prédio, conteúdo ou ambos | 2978 | 100,00% | Escolha explícita do cliente. Define quais valores são aplicáveis. Não consta nos CSVs. |
| Condições do local e aceitação da atividade | 2978 | 100,00% | Confirmar restrições e atividade aceita no produto. CNAE preenchido não comprova aceitação; o pacote não confirma toda a lista do guia. |
| CEP completo e validado | 2978 | 100,00% | CEP completo de oito dígitos. cep_agregado não é CEP completo. Logradouro, número, bairro, cidade e UF estão preenchidos. |
| Empregados confirmados nesta unidade | 2978 | 100,00% | Quantidade local confirmada ou ausência declarada. Há estimativa empresarial e folha local; sem confirmação por unidade. |
| Reconstrução ou dispensa explícita pelo escopo | 2978 | 100,00% | Reconstrução sem terreno para prédio/ambos; dispensável se conteúdo apenas. Pendência de aplicabilidade: o escopo ainda é desconhecido em todos os registros. |
| Bens, equipamentos e estoque confirmados | 2978 | 100,00% | Inventário atual, vínculo e valor de reposição na unidade. Há estimativas agregadas, sem validação atual para cotação. |
| Plano e adicionais com aceitação da atividade | 2978 | 100,00% | Sugestão do motor e validação de compatibilidade/aceitação. Plano pode ser calculado; não equivale a cotação concluída ou aceitação. |
| Refrigeração confirmada | 2978 | 100,00% | Sim/Não; se Sim, mercadorias e valores. Probabilidade estimada não substitui resposta. |
| Delivery confirmado | 2978 | 100,00% | Sim/Não; se Sim, detalhar operação. Receita/probabilidade estimadas não substituem resposta. |
| Home office confirmado | 2978 | 100,00% | Sim/Não; se Sim, bens e locais de uso. Vendas online não comprovam trabalho remoto. |
| Dinheiro/valores em caixa confirmados | 2978 | 100,00% | Sim/Não; se Sim, quantia e controles. Recebimentos não digitais não equivalem a dinheiro em caixa. |
| Eletrônicos: exposição e inventário confirmados | 2978 | 100,00% | Confirmar uso e reposição na unidade. Bens cadastrados são sinais, não confirmação atual. |
| Segurança física e controles digitais confirmados | 2978 | 100,00% | Confirmar controles efetivos; verificar requisitos de shopping quando aplicáveis. Bem SISTEMA_SEGURANCA e maturidade digital não comprovam controles. Condições para desconto não são exclusões gerais. |
| Material das paredes ausente | 2524 | 84,75% | Ausente ou NAO_DISPONIVEL. Impede verificação de combustível; não classificar ausência como material combustível. |
| Padrão construtivo ausente | 2437 | 81,83% | Ausente ou NAO_DISPONIVEL. Parâmetro de apoio ao dimensionamento, não exclusão autônoma do guia. |
| Ao menos um bem com vínculo de baixa confiança | 1827 | 61,35% | bens_baixa_confianca > 0. Prioridade de revisão de inventário; não taxa de inelegibilidade. |
| Endereço incompatível com cadastro | 656 | 22,03% | endereco_cnpj_compativel != SIM. Conferir vínculo/endereço; divergência não é proibição automática. |
| Situação cadastral irregular | 52 | 1,75% | situação = IRREGULAR. Apurar; não equiparar automaticamente a condenado ou em obra. |

## Dados disponíveis: percentual de ausência literal

| Motivo / parâmetro | Unidades | % da base | Regra e interpretação |
|---|---:|---:|---|
| CNAE | 0 | 0,00% | cnae_principal. Ausência literal. Presença não comprova confirmação contratual. Zero válido é preservado. |
| Atividade descrita | 0 | 0,00% | descricao_cnae. Ausência literal. Presença não comprova confirmação contratual. Zero válido é preservado. |
| Faturamento empresarial | 0 | 0,00% | faturamento_mensal. Ausência literal. Presença não comprova confirmação contratual. Zero válido é preservado. |
| Empregados estimados da empresa | 0 | 0,00% | quantidade_funcionarios_estimada. Ausência literal. Presença não comprova confirmação contratual. Zero válido é preservado. |
| Folha local | 0 | 0,00% | folha_pagamento_mensal. Ausência literal. Presença não comprova confirmação contratual. Zero válido é preservado. |
| Bens agregados | 0 | 0,00% | bens_ponderados. Ausência literal. Presença não comprova confirmação contratual. Zero válido é preservado. |
| Equipamentos agregados | 0 | 0,00% | equipamentos_ponderados. Ausência literal. Presença não comprova confirmação contratual. Zero válido é preservado. |
| Estoque estimado | 0 | 0,00% | estoque_medio_estimado. Ausência literal. Presença não comprova confirmação contratual. Zero válido é preservado. |
| Despesas fixas estimadas | 0 | 0,00% | despesa_fixa_mensal_estimada. Ausência literal. Presença não comprova confirmação contratual. Zero válido é preservado. |
| Aluguel identificado | 0 | 0,00% | valor_aluguel_recorrente. Ausência literal. Presença não comprova confirmação contratual. Zero válido é preservado. |

## Parâmetros propostos para o sistema

1. **IMPEDIMENTO_IDENTIFICADO**: condição proibida explicitamente registrada. Atualmente são os 78 registros EM_OBRA. Não inferir material combustível ou localização restrita por proxies.
2. **ENCAMINHAMENTO_PERSONALIZADO**: prédio/conteúdo acima de R$ 7,5 milhões. Soma parcial inferior não confirma enquadramento sem escopo e reconstrução aplicável.
3. **PENDENTE_CONFIRMACAO**: falta de informação aplicável, estimativas não confirmadas, divergência cadastral ou irregularidade a esclarecer. Não é rejeição automática.
4. **SEM_LACUNAS_MINIMAS_DEMONSTRADAS**: informações mínimas aplicáveis verificadas, ainda sujeito a aceitação oficial. Nenhum registro pode ser demonstrado nessa condição apenas com o pacote atual.
5. Campos condicionais: **SIM / NAO / DESCONHECIDO / NAO_APLICAVEL**, com justificativa para dispensa. Reconstrução é exigida para prédio/ambos; requisitos do shopping condicionam desconto, não aceitação universal.
6. Não misturar motivos de impedimento e informação faltante em uma nota com pesos arbitrários. Usar contagem de estabelecimentos por motivo para priorizar a coleta.

## Prioridade de coleta

Primeiro, identificação legal, relação com o imóvel, escopo, CEP completo e declarações de elegibilidade. Depois, revisar paredes (84,75% ausentes), padrão construtivo (81,83%), vínculo de bens (61,35% com ao menos um bem de baixa confiança) e endereço (22,03% divergentes). Os 52 registros IRREGULAR exigem esclarecimento; não foram contabilizados como inelegíveis. Há 956 unidades pertencentes a empresas com múltiplos estabelecimentos: não distribuir faturamento ou empregados igualmente sem evidência. Isso é contexto de qualidade, não falta de dado autônoma.

Ausências estruturais do pacote anônimo não representam falhas do cliente. Valores de bens, despesas, estoque e aluguel podem estar preenchidos e ainda exigir confirmação de reposição/aplicabilidade. Sem preços, franquias e aceitação, não se trata de proposta concluída.

Reproduzir: `.venv/Scripts/python.exe scripts/analisar_pendencias_cotacao.py`. Saídas agregadas, sem identificação individual. O JSON registra os hashes das entradas para auditoria.
