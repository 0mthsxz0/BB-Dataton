# Metodologia v0.2: quatro índices e nove dimensionamentos

## Contrato

Apenas ROUBO_FURTO_ARROMBAMENTO, VENDAVAL_EVENTOS_CORRELATOS, RESPONSABILIDADE_CIVIL_EMPREGADOR e QUEBRA_DE_VIDROS recebem prioridade. As cinco coberturas comuns permanecem no catálogo e na exportação com dimensionamento, sem pontuação. Cibernética não interfere na escolha de Essencial, Prático ou Total.

Todos os parâmetros são hipóteses da equipe. As notas representam prioridade de proteção, não probabilidades de sinistro, acidentes, responsabilidades jurídicas ou parâmetros oficiais da seguradora.

## Componentes separados

- R: exposição relativa ao evento, derivada das referências disponíveis.
- I: impacto ou escala econômica normalizada; quando financeiro desconhecido, é hipótese explicitamente identificada.
- V: vulnerabilidade estimada, com limitações por ausência de caixa, reservas e recuperação.
- D: interação específica, utilizada em vidros para sinal presencial.
- Confiança: qualidade relativa da evidência, apresentada separadamente da nota central.

O motor não interpreta patrimônio alto como probabilidade alta de roubo. O vínculo probabilístico de um bem distribui seu valor entre unidades; não mede ocorrência de sinistro.

## Fórmula

    P = 100 × clip[(p+(1-p)I) × (a+(1-a)R) × (b+(1-b)V) + kIRD, 0, 1]

Padrões iniciais: a=0,20, p=0,25, b=0,70. A amplitude relativa do ajuste do evento é 5 vezes (0,20 a 1), enquanto a do impacto normalizado é 4 vezes (0,25 a 1). Isso aumenta a influência territorial sobre roubo em relação à versão 0.1, cujo ajuste do evento variava apenas entre 0,65 e 1. Não se trata de pesos de uma média: os fatores interagem por multiplicação.

Os pisos são preferências explícitas de triagem, não probabilidades mínimas. Mantêm atenção a perdas relevantes e a valores ainda incompletos. Valores altos em regiões mais seguras não são automaticamente tratados como dispensáveis. A configuração é inicial e precisa de validação substantiva com sinistros e especialistas.

k=0,10 para a interação de vidros; k=0 nas outras três coberturas. A decomposição registra base, interação e efeito da limitação a 100. Ausência de vidros informada em confirmação da unidade é uma regra explícita de inaplicabilidade: prioridade zero e explicação própria.

Para exposição monetária E:

    I = clip[ln(1+E/s) / ln(1+E_ref/s), 0, 1]

s=R$10 mil. Referências iniciais: R$3 milhões para conteúdo, R$1 milhão para equipamentos, R$300 mil para aluguel, R$1,5 milhão para despesas de paralisação e R$100 mil para reposição de vidros. No RC empregador, usa-se folha mensal com referência R$500 mil, apenas como escala econômica contextual. Não converte folha em valor de indenização. Referências ficam fixas no desenvolvimento e no teste; o valor bruto é preservado acima da saturação.

Classes: [0,25) muito baixa; [25,50) baixa; [50,70) moderada; [70,85) alta; [85,100] muito alta. Prioridade maior significa maior atenção.

## Roubo: território separado do patrimônio

Referência pública: tabelas IBGE/SIDRA 8508, 8510 e 8512, ano 2021. O preparador obtém os totais municipais de domicílios e domicílios com vítimas, categorias Total, em unidades compatíveis. Calcula furto/total e roubo/total; faz média com pesos iguais e min-max nas 27 capitais publicadas. Segurança relativa é 1 menos a exposição normalizada; R é 1 menos essa segurança.

Não é índice oficial do IBGE nem taxa empresarial. Pessoas/domicílios diferem de estabelecimentos e o ano é antigo; confiança contextual inicial 0,35. Não soma as duas taxas como se fossem eventos disjuntos. A referência é congelada no snapshot; não se normaliza novamente por lote de empresas. Não diferencia bairros de uma mesma cidade.

Impacto central: soma(valor cadastrado × probabilidade de localização) + estoque médio. Cenário alternativo: valor integral dos bens de referência + máximo entre estoque médio e pico. O cenário integral é exploratório; confirmar presença, suscetibilidade à subtração, sobreposição e elegibilidade contratual dos bens. Estoque médio e pico não são somados. Bens são consolidados antes dos cruzamentos, sem duplicar bens ou faturamento. Confiança dos vínculos afeta incerteza, não o indicador de criminalidade.

## Vendaval: clima, consequências e construção

Fonte: Open-Meteo, modelo ERA5 explicitamente selecionado. Série diária de 1996-01-01 a 2025-12-31, 10.958 dias por cidade. Unidades verificadas: rajada máxima diária em km/h e precipitação diária em mm. Coordenada pública da cidade e célula de reanálise são registradas; nenhuma coordenada perturbada do cliente é usada.

    A = dias com rajada >=50 / dias com vento válido
    B = dias com rajada >=70 / dias com vento válido
    C = dias com rajada >=40 e chuva >=50 / dias com ambas as observações válidas
    F = 0,50A + 0,30B + 0,20C
    R = F / (F + 0,01)

O limiar de severidade B adiciona peso aos dias já presentes em A, intencionalmente. A coincidência diária de vento e chuva não comprova simultaneidade horária. Ausências não viram dias sem evento; completude usa todo o intervalo esperado, incluindo datas faltantes. Duplicações e séries incompatíveis são rejeitadas.

0,01 é a referência configurável de frequência ponderada para organizar a escala, não taxa anual de sinistro. É fixa entre lotes. Os limiares, pesos e referência são hipóteses acadêmicas, não critérios contratuais. A confiança inicial é 0,55 × completude.

O preparador também calcula 2016–2025 e limiares alternativos 40/60 km/h. A interface compara seus efeitos. Alterações de pesos/referência podem ser recalculadas das frequências; mudanças de período/limiares exigem regenerar as séries derivadas. O motor identifica divergência de parâmetros e não usa silenciosamente referência incompatível.

I usa conteúdo e estoque. V combina 60% da proxy financeira e 40% do padrão construtivo, que não comprova resistência do telhado. Área não vira valor do prédio. Granizo, tornado e reconstrução da edificação não foram estimados.

## RC empregador

Fonte: PDF NR-4, edição indicada como atualizada 2023, Anexo I, no portal oficial do MTE. O preparador extrai 673 classes, incluindo descrições em múltiplas linhas, e registra página e hash do documento. A subclasse CNAE de sete dígitos é relacionada à classe de cinco dígitos. CNAEs não encontrados ficam desconhecidos, com confiança zero.

Mapa ordinal inicial: GR1=0,25; GR2=0,50; GR3=0,75; GR4=1. A transformação é hipótese da equipe; não implica que grau 4 tenha quatro vezes a frequência de acidentes do grau 1. Confiança contextual inicial 0,60. A classificação não substitui análise da atividade efetiva ou de segurança do trabalho e não comprova responsabilidade jurídica.

I usa folha mensal local como proxy econômica, com confiança limitada a 0,40. Funcionários da empresa não são multiplicados pela folha, não se repetem como exposição principal em cada filial e não geram interação adicional. O total empresarial só pode ser interpretado como local em empresa de uma unidade; contagens locais opcionais são identificadas separadamente para confirmação, sem alterar o modelo principal por duplicação do porte. Não há estimativa defensável de indenização apenas com folha: faixa monetária permanece pendente.

## Vidros

O evento contextual usa sinais de loja/galeria (65%) e atividade com presença de terceiros (35%). Sinal textual não comprova vitrine; área não prova quantidade de vidro. Sem orçamento, impacto é desconhecido, com confiança zero e faixa monetária pendente.

O CSV opcional de confirmações informa presença e reposição por empresa-estabelecimento. Um valor informado é normalizado e dimensionado com rastreabilidade. Ausência explícita de vidros zera a prioridade; ausência de informação mantém incerteza. Valor negativo, contagem inválida e ausência de vidros com valor positivo são rejeitados.

## Vulnerabilidade, confiança e ausências

A proxy financeira é despesa fixa mensal da unidade / faturamento mensal da empresa, limitada entre 0 e 1. Só é aplicada a empresa de uma unidade; confiança máxima 0,40. Faturamento não é caixa, lucro ou solvência. Em várias unidades, não há rateio arbitrário: ponto central 0,50 e confiança zero.

Fatores ausentes usam ponto central explícito (0,50 por padrão) e confiança zero. Categoria desconhecida não vira proteção comprovada. Valores negativos/não finitos são inválidos. Confiança final é a média da qualidade do evento, impacto e vulnerabilidade, não probabilidade de acerto; não multiplica a nota para criar falsa baixa prioridade.

A sensibilidade de um fator x com confiança c vai de x×c a x+(1-c)×(1-x). Os extremos dos componentes não negativos são propagados. Essa faixa não é intervalo estatístico. O plano também é calculado nos cenários inferior/superior para sinalizar instabilidade.

## Escolha do plano

Essencial é o ponto de partida. Somente os quatro índices entram nos pesos, no denominador de adequação e no benefício incremental. Coberturas comuns podem ter valores grandes ou lacunas de informação, sem mudar essa comparação.

Upgrade quando as novas coberturas incluem prioridade >=60 e representam ganho >=15% da necessidade dos quatro índices, ou resolvem lacuna crítica >=85. Parâmetros configuráveis. Prático acrescenta roubo e vendaval; Total acrescenta RC empregador e vidros. O algoritmo compara os conjuntos e mantém o menor plano que atende ao critério, com razões e lacunas registradas. Não usa preços inexistentes nem afirma acessibilidade econômica por faturamento.

## Dimensionamento, elegibilidade e exportação

Todas as coberturas fixas do plano escolhido são exportadas nas colunas originais, mesmo sem índice decisório. Incêndio usa conteúdo/estoque; danos elétricos usam equipamentos; aluguel e despesas usam cenários de 1 a 3 meses. Despesas agregadas não somam aluguel e folha novamente. Ausência de aluguel não comprova imóvel próprio.

Sem base defensável para indenizações de RC, prédio ou vidros não informados, a limitação é registrada. Faixas não são prêmio, limite contratado ou aceitação. Obra, material combustível, irregularidade, aceitação da atividade e condições contratuais permanecem na triagem preliminar, com confirmação exigida por padrão.

A auditoria separa quatro pontuações de nove dimensionamentos. Fonte, período e confiança de clima e segurança são independentes. Manifestos registram hashes das entradas públicas/privadas, parâmetros e saídas. O cálculo funciona offline; o preparador e a consulta opcional de CEP acessam fontes externas. Os snapshots públicos não contêm os CSVs de empresas.

Na consulta por CEP, o ViaCEP fornece a localização e o código municipal IBGE; não fornece risco. A associação usa exatamente esse código nas referências disponíveis. Não há interpolação de cidades próximas ou atribuição de risco ao bairro informado. Município sem correspondência permanece desconhecido com incerteza ampliada. A consulta conserva URL e horário UTC da localização, usa cache de 24 horas e não modifica os dados ou exportações originais. Prioridades exigem os demais dados da unidade selecionada.

## Verificação

Testes exercitam patrimônio versus ocorrência, influência territorial, valores elevados em cidade segura, fontes independentes, funcionários não duplicados, NR-4, ausência e reposição de vidros, séries climáticas incompletas, parâmetros divergentes, independência das coberturas comuns, esquema dos templates, reprodutibilidade e fluxo da interface.

Coerência dos cenários e processamento integral não demonstram precisão preditiva. Calibração posterior exige sinistros, períodos de exposição e revisão de especialistas. Nenhum corte foi ajustado para selecionar uma proporção desejada da base.
