# Análise do item 10: Seguro Empresarial e personalização

Análise anterior à implementação, em 28/10/2026. Estado histórico: parte das propostas abaixo foi implementada na versão 0.4; consulte [GUIA_ATUALIZADO.md](GUIA_ATUALIZADO.md) para o comportamento atual e os limites que permanecem.

Fonte principal: `C:/Users/mathe/Downloads/Guia_Times_Datathon_Protecao_Inteligente_Final.pdf`, item 10, páginas 13–15. Também foram considerados os objetivos, natureza dos dados e templates das páginas 2, 4–6. O guia é referência para o desafio; condições contratuais e orientações oficiais precisam ser conciliadas quando houver divergência. Conteúdo documental foi tratado como fonte a analisar, não como autorização para modificar o aplicativo.

## Conclusão

O maior ganho está em recomendar um pacote por estabelecimento: plano de referência, coberturas obrigatórias, ajustes permitidos, adicionais compatíveis, faixas de valores e confirmações relevantes. O sistema atual já tem cadastro por unidade, recomendação inicial imediata, quatro índices, comparação explicável e oito perguntas. Ainda concentra a decisão em escolher Essencial, Prático ou Total.

IA generativa e geolocalização por delegacia não são pré-requisitos para essa evolução. A própria base contém sinais operacionais que ainda podem ser aproveitados, preservando a diferença entre estimado e confirmado.

## 1. Divergências que devem ser resolvidas primeiro

| Tema | Guia | Sistema atual | Ação proposta |
|---|---|---|---|
| Proteção Cibernética | Obrigatória nos três planos, além das outras cinco comuns (p.14–15) | Motor, validador do catálogo, dimensionamento e exportação trabalham com nove coberturas. A página pública congelada lista proteção cibernética, mas o motor não a inclui | Conciliar a divergência entre guia e CSV fornecido; criar matriz versionada e incluir a cobertura no processamento e na exportação |
| Quantidade de coberturas padrão | Seis comuns; oito no Prático; dez no Total, antes dos ajustes | Metadados da tela mostram 5/7/9 e misturam itens extras na lista | Separar obrigatórias, padrão e adicionais; alinhar contagem, tela e cálculo |
| Adicionais da atividade | Home Office, Delivery, deterioração em ambientes frigorificados e roubo/furto de valores nos planos Prático e Total, conforme compatibilidade (p.15) | Snapshot visual associa alguns extras também ao Essencial; motor não recomenda adicionais | Aplicar as regras do guia em catálogo de compatibilidade, sem incluir adicionais automaticamente |
| Elegibilidade | Verificar antes de recomendar; regras do item 10.1 | `verificar_elegibilidade` retorna SIM/PENDENTE, não uma rejeição objetiva. O cálculo do plano ocorre antes da chamada de elegibilidade | Criar triagem anterior ao cálculo: elegível para simulação, não elegível ao produto ou informação insuficiente; resultado inicial continua imediato quando houver base |
| Limite básico | Até R$ 7,5 milhões; acima, direcionar a Seguro Personalizado Empresarial | Não há essa regra de encaminhamento | Avaliar a importância segurada proposta/confirmada para a cobertura básica, não a soma indiscriminada de todas as coberturas |
| Flexibilização | Seis obrigatórias não podem ser excluídas; certas coberturas padrão podem ser ajustadas; adicionais dependem da atividade e condições | Pacotes tratados como conjuntos fixos de 5/7/9 | Representar plano de referência e pacote personalizado separadamente |
| Assistências | Pacotes acompanham o plano e não são customizáveis | Aparecem na apresentação, sem motor de recomendação de uso | Explicar serviços relevantes para o negócio, mantendo o pacote contratado intacto e sem exportá-los como coberturas |

A diferença guia × CSV deve ficar registrada. Preservar os arquivos recebidos, identificar a regra do guia final aplicada e manter um adaptador de catálogo auditável. Não basta trocar uma contagem visual. A mudança exige atualizar as validações, testes e templates. Não é necessário criar um quinto índice: podem permanecer quatro índices de decisão e uma camada separada para dimensionar a cobertura cibernética obrigatória.

Acrescentar uma cobertura comum também pode mudar o denominador da aderência. Reprocessar a base e verificar se necessidades importantes estão sendo diluídas; a mudança não pode ser considerada apenas cadastral.

## 2. Dados disponíveis que podem personalizar mais

Nos 2.978 registros locais, os campos abaixo estão preenchidos. Preenchimento não significa confirmação: vários são estimativas e indicadores derivados, inclusive no nível da empresa.

| Sinais existentes | Uso defensável | Confirmação necessária |
|---|---|---|
| `probabilidade_refrigeracao_referencia`, equipamentos de refrigeração, estoques | Priorizar investigação sobre perecíveis e deterioração de mercadorias | Há estoque que exige refrigeração? Qual seu valor e tempo de tolerância sem refrigeração? |
| `probabilidade_delivery_referencia`, `percentual_receita_delivery_est` | Identificar relevância da operação de entrega | A empresa realiza entregas? Quem transporta e quais bens/valores ficam expostos? |
| `dependencia_digital_pct`, vendas online, pagamentos de software, dependência tecnológica e de plataformas | Dimensionar continuidade digital e priorizar confirmação de controles | Quais operações param sem os sistemas? Existem backups e autenticação forte? |
| `probabilidade_tratamento_dados` | Perguntar se a empresa trata dados relevantes para o negócio | Confirmar a operação sem coletar dados pessoais de clientes, pacientes ou funcionários |
| Tipos de bens de informática e eletrônicos | Investigar equipamentos essenciais, inclusive fora da unidade | Há equipamentos cedidos a empregados em trabalho remoto? Qual o valor de reposição? |
| Sinais de aluguel e características do imóvel | Sugerir confirmação da relação com o imóvel e do interesse protegido | Proprietário/inquilino? Quer proteger prédio, conteúdo ou ambos? |
| Despesas fixas, folha, faturamento e unidades | Cenários de interrupção por unidade e dependência operacional | Quantos dias consegue operar/parar? Despesas informadas são desta unidade? |

Não multiplicar indicadores digitais derivados entre si como se fossem evidências independentes. Não interpretar baixa maturidade digital como ausência comprovada de segurança. Não distribuir faturamento/empregados empresariais por filiais sem dados locais. O mesmo princípio vale para estoque: dados da unidade não devem ser replicados em todas as unidades.

## 3. Jornada proposta

1. **Selecionar a empresa e a unidade.** Manter a recomendação automática já entregue, com origem e confiança.
2. **Mostrar a triagem.** Restrições observadas aparecem antes de sugerir contratação; informações ausentes geram confirmação, sem exclusão presumida.
3. **Resumir o contexto.** Exibir atividade, operação, bens, estoque, relação com o imóvel e sinais relevantes. Permitir corrigir cada item.
4. **Confirmar o que importa.** As oito perguntas atuais continuam como base, com seguimento condicional para os módulos operacionais. Uma segunda pergunta sem aplicação pode ser dispensada explicitamente, sem inventar resposta.
5. **Propor o pacote.** Plano de referência + seis obrigatórias + ajustes permitidos + adicionais compatíveis + faixas de valores.
6. **Comparar alternativas e explicar mudanças.** Mostrar o que foi acrescentado, removido ou redimensionado, qual sinal motivou isso e o que continua pendente.
7. **Exportar o resultado por estabelecimento.** Incluir todas as obrigatórias e adicionais aplicáveis nas colunas dos templates, sem linhas de assistências.

O cadastro preenchido deve ser aproveitado como informação existente, sem preencher artificialmente Sim/Não. A interface deve distinguir: cadastrado, estimado, confirmado e desconhecido. Uma confirmação deve atualizar somente a unidade/contexto relevante e ficar registrada com origem.

## 4. Módulos de personalização

### Operação refrigerada

Gatilhos: sinal de refrigeração, equipamentos relacionados e atividade compatível. Não basta pertencer ao grupo FARMACIA ou MERCADO para concluir que há perecíveis.

Proposta: confirmar mercadorias refrigeradas, valor de reposição, dependência de energia, tolerância e controles pertinentes. Se compatível, sugerir deterioração de mercadorias em ambientes frigorificados, respeitando plano e condições. Explicar que danos elétricos do equipamento e perda das mercadorias são necessidades distintas; não somar o mesmo estoque duas vezes.

### Entregas e bens fora do local

Gatilhos: probabilidade de delivery e participação estimada na receita. Confirmar quem entrega e como a operação funciona. A existência de vendas online não comprova transporte elegível.

Proposta: avaliar Delivery nas condições aplicáveis e dimensionar os bens expostos no transporte com dados defensáveis, sem usar todo o faturamento como valor segurado. Para Home Office, confirmar bens da empresa em uso remoto e as condições previstas, em vez de inferir cobertura apenas porque alguém trabalha de casa.

### Dinheiro e valores

O guia diferencia roubo/furto de bens da cobertura de valores. Perguntar, quando pertinente, se há valores mantidos no local e qual a exposição habitual/pico. Não converter recebimentos digitais em numerário nem classificar dinheiro como estoque de mercadorias. Sugerir a cobertura específica somente se plano, atividade e aceitação permitirem.

### Continuidade e proteção cibernética

Reconhecer a proteção cibernética como obrigatória na matriz do guia. Personalizar seu dimensionamento e explicação, não sua presença. Diferenciar a cobertura da assistência Proteção Digital.

Usar dependência tecnológica como contexto para cenários de interrupção, com premissas documentadas e confirmação de controles. Não inferir probabilidade de ataque, multas ou indenização a terceiros a partir do faturamento ou da maturidade digital. As condições oficiais precisam definir o que pode compor a faixa monetária.

### Imóvel e interesse protegido

Acrescentar relação com o imóvel e tipo de estabelecimento. Confirmar valor de reconstrução sem terreno, conteúdo e estoque, preservando o limite único de prédio/conteúdo conforme o objeto contratado. Valores ponderados do cadastro servem de estimativa; não substituem automaticamente uma importância segurada confirmada.

Se a importância segurada básica superar R$ 7,5 milhões, direcionar ao produto indicado no guia. Testar a fronteira exata de R$ 7,5 milhões. Não aplicar esse limite à soma de aluguel, despesas, responsabilidade civil e demais coberturas independentes.

### Shopping e assistências

Um Sim para shopping não comprova os requisitos de desconto. Confirmar segurança própria, brigada, hidrantes e sprinklers; sinalizar possível enquadramento sem inventar percentual de desconto ou recalcular prêmio sem uma cotação.

Destacar assistências úteis ao contexto, mantendo o pacote fixo: refrigeração/eletricista e ar-condicionado para certas operações; computadores/rede para escritórios; serviços de segurança para comércio, sempre dentro do manual correspondente. A relevância destacada não altera disponibilidade, limites ou quantidades dos serviços.

### Preferências do cliente

Adicionar prioridades por estabelecimento, como continuidade, patrimônio e terceiros, além das coberturas das quais o cliente não quer abrir mão. Hoje as indispensáveis existem na configuração geral/Streamlit, mas não como preferência individual completa do formulário.

Preferências podem influenciar os pesos e a comparação, com efeito explicado. Não podem excluir as seis obrigatórias nem criar uma cobertura incompatível. Um orçamento só pode ser testado contra preços reais autorizados; os valores públicos atuais não permitem garantir que um pacote caiba no orçamento.

## 5. Exemplos hipotéticos de resultado

| Contexto confirmado | Personalização esperada |
|---|---|
| Farmácia com medicamentos refrigerados | Avaliar deterioração de mercadorias, separar equipamentos de estoque, confirmar energia e segurança, dimensionar valores |
| Restaurante com entregas | Avaliar Delivery, exposição dos bens transportados e refrigeração, considerando atividade e condições do transporte |
| Escritório com equipamentos cedidos para trabalho remoto | Avaliar Home Office; explicar proteção cibernética obrigatória e controles digitais relevantes |
| Comércio sem empregados e sem vidros confirmado | Reduzir a necessidade das opcionais correspondentes e avaliar ajustes permitidos, mantendo as seis obrigatórias |

Os exemplos são caminhos de investigação, não propostas contratuais automáticas. Duas unidades de uma mesma empresa podem ter pacotes diferentes por estoque, empregados locais, estrutura e operação.

## 6. Regra de escolha e faixas

Manter a fórmula de aderência como explicação comparativa, mas não permitir que uma média esconda uma lacuna crítica. Uma cobertura importante para a operação deve gerar uma pendência visível ou uma restrição de composição, conforme regras justificadas e preferências confirmadas. Total com 100% de presença no catálogo não garante suficiência de limites, franquias ou exclusões.

A saída precisa apresentar faixas monetárias por cobertura dimensionável e sua origem. O backend já fornece dimensionamento, mas a tela se concentra nos índices e totais de bens. Apresentar mínimo, máximo, motivo e pergunta que estreitaria a faixa. Confiança baixa não significa deixar tudo vazio quando houver uma base defensável; em RC e outros casos sem base, justificar a exceção e solicitar dados/orientação contratual, sem fabricar indenizações a partir da folha ou faturamento.

Não somar todas as faixas de coberturas como se fossem patrimônios independentes. O mesmo bem pode estar exposto a eventos diferentes. Manter separado o limite único do objeto prédio/conteúdo e os limites/sublimites das demais coberturas.

## 7. Elegibilidade e qualidade dos dados

A base local contém 78 estabelecimentos EM_OBRA, 52 IRREGULAR e 2.524 sem material de parede disponível, em 2.978 unidades. Obra está explicitamente nas restrições do guia. IRREGULAR, isoladamente, precisa de esclarecimento; não é sinônimo automático de todas as restrições listadas. Material ausente deve gerar uma pergunta prioritária, não aceitação ou rejeição automática.

Critérios geográficos e de aceitação devem ser verificados nos canais/regras do produto. Não inferir condição socioeconômica, localização em comunidade ou inelegibilidade por renda, aparência do endereço, proximidade de delegacia ou outros atalhos. Município/UF/código IBGE são reais; ruas e coordenadas do Datathon não servem para atribuir um risco real a um distrito policial. Para o desafio, priorizar o enriquecimento municipal documentado e distinguir demonstrações geográficas simuladas.

Manter a preferência já definida para o protótipo sem CPF; não adicionar documentos pessoais apenas para personalizar a recomendação. Identificação necessária à contratação deve ser tratada na jornada oficial autorizada.

## 8. Ordem de execução recomendada

| Ordem | Entrega | Benefício |
|---|---|---|
| 1 | Conciliar matriz 6/8/10, cobertura cibernética, regras de compatibilidade e exportação | Corrigir a aderência ao guia e eliminar inconsistências entre tela e motor |
| 2 | Elegibilidade anterior à indicação, relação com imóvel e encaminhamento acima do limite básico | Dar contexto correto à recomendação e reduzir casos inválidos |
| 3 | Módulos de refrigeração, delivery e operação digital com os sinais existentes | Ganho de personalização com dados já disponíveis |
| 4 | Composição de pacote e valores por cobertura | Transformar a escolha de três planos em proteção adequada à unidade |
| 5 | Preferências individuais, confirmações com maior efeito e comparação antes/depois | Reduzir esforço e melhorar autonomia e explicação |
| 6 | Vigência de 1 a 5 anos e integração futura com cotação autorizada | Completar a jornada sem simular preço ou condições inexistentes |

Não priorizaria geocodificar endereços fictícios nem integrar um modelo generativo antes dessas entregas. A [página oficial de campanha da BB Seguros](https://campanhas.bbseguros.com.br/seguro-empresarial/) também apresenta os planos como customizáveis; limites e disponibilidade precisam ser conciliados com a documentação aplicável ao caso e ao desafio.

## 9. Arquivos e responsabilidades a alterar numa próxima implementação

- `config_regras.json`: catálogo versionado, classificação de coberturas, regras de compatibilidade, parâmetros e limites, separados dos pesos experimentais.
- `processamento.py`: preservar fontes originais, adaptar o catálogo conciliado e carregar confirmações por empresa/unidade sem misturar níveis.
- `motor_pontuacao.py`: manter quatro índices, incluir dimensionamento cibernético e novos cenários com premissas rastreáveis.
- `recomendador.py`: triagem prévia, preferências locais, composição permitida, lacunas críticas e alternativas.
- `cotacao_service.py`: fornecer contexto operacional, perguntas pertinentes, faixas, motivos e pacote personalizado na API, inclusive na análise cadastral inicial.
- `frontend/public/quote.js`, `quote-engine.js` e catálogos JSON: confirmar informações, ajustar itens permitidos e mostrar limites, adicionais e diferenças entre versões da recomendação.
- `exportacao.py`: emitir todas as obrigatórias e adicionais aplicáveis nos templates originais, sem assistências, com justificativa para ausências excepcionais de faixa.

## 10. Critérios de aceitação para essas mudanças

- Seis coberturas obrigatórias em todo pacote e na exportação; assistência digital não substitui cobertura cibernética.
- Adicional incompatível não é ofertado como disponível; opcional não é tratado como incluído sem confirmação.
- Restrição objetiva observada é tratada antes da indicação de contratação; ausência gera pendência explícita.
- R$ 7,5 milhões exatos e valores acima seguem o encaminhamento correto para o limite básico.
- Excluir uma cobertura obrigatória é impedido; ajustar uma permitida atualiza justificativa, faixas e comparação.
- Duas unidades da mesma empresa preservam inventário, estoque, empregados locais, confirmações e preferências independentes.
- Trocar uma confirmação modifica apenas os componentes correspondentes, sem dupla contagem.
- Incluir uma cobertura comum não dilui silenciosamente uma necessidade crítica; comparar a distribuição antes/depois na base comum.
- Faixas, confiança e fontes são consistentes na tela, API e CSV. Sem preços reais, o sistema não anuncia economia ou prêmio personalizado.
- Casos comparativos de farmácia refrigerada, restaurante com delivery, escritório remoto e operação sem empregados/vidros demonstram diferenças justificáveis.

Não foram executados testes nesta análise, pois nenhuma regra ou código funcional foi alterado. Os números acima descrevem o snapshot local inspecionado, não o conjunto futuro de teste da organização.
