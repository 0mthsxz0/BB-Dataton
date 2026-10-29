# Metodologia v0.4: quatro índices, dez necessidades e SSP

## Contrato

ROUBO_FURTO_ARROMBAMENTO, VENDAVAL_EVENTOS_CORRELATOS, RESPONSABILIDADE_CIVIL_EMPREGADOR e QUEBRA_DE_VIDROS preservam seus índices multifatoriais contínuos. As seis coberturas comuns recebem pontuações heurísticas de preferência, explicitamente separadas dos modelos físicos. As dez necessidades entram na aderência; as dez coberturas continuam com dimensionamento. Proteção cibernética é comum obrigatória na política do guia: preferência experimental 30 + 60 × dependência tecnológica, sem índice de ataque ou indenização inventada. A faixa monetária fica pendente de base contratual defensável.

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

O snapshot histórico IBGE/SIDRA 8508, 8510 e 8512, ano 2021, descreve vitimização domiciliar nas 27 capitais. A política `seguranca-1.0` o exclui do índice empresarial por incompatibilidade de população e fenômeno observado. Seus valores brutos são conservados para consulta histórica.

Somente referências comerciais compatíveis, com ano encerrado, doze meses, estabelecimentos do mesmo ano e fonte, integridade conferida e até 24 meses após dezembro do ano observado podem contribuir. Dados inadequados deixam R=0,5 e confiança territorial zero. As regras e a inspeção do Sinesp VDE 2025 estão em [CONFIABILIDADE_SEGURANCA.md](CONFIABILIDADE_SEGURANCA.md). O VDE inspecionado não contém roubo em comércio e não substitui essa medida. Referências SSP elegíveis continuam experimentais, sem calibração atuarial e sem precisão de bairro ou rua.

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

Aderência(plano) = soma(peso × pontos das necessidades presentes) / soma(peso × pontos das dez necessidades). Meta inicial de 80%, configurável. Os pesos iniciais são 1. O menor nível que alcança a meta e contém todas as coberturas indispensáveis é escolhido. Uma indispensável vale mesmo com zero pontos e meta zero. Não há preços ou teste de orçamento; não se afirma menor custo. Os cortes antigos de upgrade foram retirados.

Os quatro índices entram com sua precisão contínua, sem conversão em 25/55/85 nem nova multiplicação pelo patrimônio. As seis heurísticas iniciais, inspiradas no MVP enviado, são:

| Necessidade comum | Preferência inicial |
|---|---|
| Incêndio | 70 com inventário; 50 sem inventário |
| Danos elétricos | 30 + 60 × dependência tecnológica entre 0 e 1 |
| Aluguel | 75 com sinal de pagamento; 25 sem sinal; desconhecido 50 |
| RC estabelecimento | 70 com sinal de loja/galeria; 50 sem sinal |
| Despesas fixas | 30 + 60 × despesa/(despesa + 30.000) |

Todos os coeficientes estão em heuristicas_comuns. Ausências usam ponto central 50 com confiança zero. Essas regras de preferência não medem probabilidade nem perda esperada. O dimensionamento financeiro continua separado. Confiança contextual das heurísticas: 0,35 para incêndio/elétrico/aluguel, 0,30 para RC estabelecimento e 0,40 para despesas, quando há sinal observado; são hipóteses conservadoras. A confiança geral é a média ponderada das dez necessidades, não acurácia.

Aderência mede presença binária no catálogo: Total apresenta 100% das necessidades, sem garantir que limites, franquias ou exclusões atendam a qualquer perda. A contribuição de cada necessidade, a conta e as indispensáveis são auditadas. Preferências globais da sessão também se aplicam aos lotes exportados. As seis comuns agora influenciam o denominador e podem alterar a escolha, conforme a nova instrução do projeto.

As faixas de cada pontuação preservam a regra x×c a x+(1-c)×(100-x) em pontos. Para cada plano, o mínimo de aderência usa coberturas presentes no limite inferior e ausentes no superior; o máximo usa o inverso. Não basta reduzir ou aumentar todas as notas juntas, porque a aderência é uma razão. O intervalo não é estatístico. A comparação sinaliza o menor plano possível e o menor que atende em toda essa faixa conservadora, respeitando as indispensáveis.

## Segurança SSP

O importador recebe planilhas anuais com doze meses, natureza exata Roubo em Comércio, código IBGE e origem explícita. Não infere região administrativa pelo CEP. Regiões são consolidadas municipalmente apenas com declaração de cobertura completa sem sobreposição; duplicação de região ou mistura explícita de total municipal com regiões é recusada. Essa declaração precisa de revisão humana da fonte; o código não comprova sozinho a completude geográfica.

A taxa é soma(ocorrências) / soma(estabelecimentos) × 1.000 no mesmo ano e território. Não usa média simples das taxas regionais. Exposição R = taxa/(taxa + referência fixa); segurança = 1-R. Referência experimental inicial: 100 ocorrências por mil estabelecimentos. É configurável no preparador, não recalibrada pelo subconjunto consultado e não é um parâmetro atuarial validado. Um único município pode ter indicador porque a escala é fixa. Ocorrências repetidas não identificam empresas distintas; a taxa não é probabilidade.

Sem denominador ou com ano incompleto, o indicador permanece indisponível: ponto central 0,50 e confiança zero, sem transformar somas de ausências em zero. Contagem anual observada é conservada quando possível. Com dados completos, confiança contextual inicial 0,55; definições e subnotificação continuam limitações. Não se misturam anos nem denominadores regionais ausentes com taxas válidas. Fontes de estados diferentes exigem revisão de equivalência antes de comparação.

A saída seguranca_ssp.csv sobrepõe apenas a segurança dos municípios nela presentes, conservando clima e NR-4. Fora da cobertura SSP usa a referência municipal existente; uma linha SSP explicitamente indisponível não vira ausência silenciosa. Campos antigos de vitimização domiciliar são limpos quando substituídos. Referências SSP são usadas no cadastro, no CEP e nos lotes. Metodologia, período, contagens, denominador, hashes e horário de preparo do indicador aparecem na auditoria. Esse horário não comprova a data de atualização do portal original.

Downloads usam URLs HTTPS explícitas do manifesto, com cache local; --atualizar reconstrói a partir de novos downloads. O importador não descobre portais, não agenda execuções e não promete compatibilidade com qualquer formato estadual. A análise lê o snapshot preparado. A escala de exposição SSP não é intercambiável com a PNAD: a origem aparece no resultado e qualquer troca deve ser revisada pela equipe.

## Dimensionamento, elegibilidade e exportação

Todas as coberturas fixas do plano escolhido são exportadas nas colunas originais, mesmo sem índice decisório. Incêndio usa conteúdo/estoque; danos elétricos usam equipamentos; aluguel e despesas usam cenários de 1 a 3 meses. Despesas agregadas não somam aluguel e folha novamente. Ausência de aluguel não comprova imóvel próprio.

Sem base defensável para indenizações de RC, prédio ou vidros não informados, a limitação é registrada. Faixas não são prêmio, limite contratado ou aceitação. Obra, material combustível, irregularidade, aceitação da atividade e condições contratuais permanecem na triagem preliminar, com confirmação exigida por padrão.

A auditoria separa quatro pontuações de dez dimensionamentos. Fonte, período e confiança de clima e segurança são independentes. Manifestos registram hashes das entradas públicas/privadas, parâmetros e saídas. O cálculo funciona offline; o preparador e a resolução opcional do município IBGE acessam fontes externas. Os snapshots públicos não contêm os CSVs de empresas.

Na consulta por CEP, o ViaCEP fornece a localização e o código municipal IBGE; não fornece risco. A associação usa exatamente esse código nas referências disponíveis. Não há interpolação de cidades próximas ou atribuição de risco ao bairro informado. Município sem correspondência permanece desconhecido com incerteza ampliada. A consulta conserva URL e horário UTC da localização, usa cache de 24 horas e não modifica os dados ou exportações originais. Prioridades exigem os demais dados da unidade selecionada.

## Verificação

Testes exercitam patrimônio versus ocorrência, influência territorial, valores elevados em cidade segura, fontes independentes, funcionários não duplicados, NR-4, ausência e reposição de vidros, séries climáticas incompletas, parâmetros divergentes, participação das dez necessidades, indispensáveis e meta de aderência, esquema dos templates, reprodutibilidade e fluxo da interface.

Coerência dos cenários e processamento integral não demonstram precisão preditiva. Calibração posterior exige sinistros, períodos de exposição e revisão de especialistas. Nenhum corte foi ajustado para selecionar uma proporção desejada da base.


## Atualização do guia item 10 (0.4)

A matriz efetiva contém 6/8/10 coberturas. `produto.py` adapta em memória o catálogo 5/7/9 recebido, sem modificar CSVs originais; os hashes de entrada são preservados. `frontend/public/product-rules.json` versiona a fonte e a conciliação entre o guia e a campanha pública. O CSV e a campanha não incluem a sexta comum; o snapshot da página principal a associa aos planos. Extras de atividade seguem Prático/Total nesta simulação, embora a campanha diga qualquer plano conforme atividade. Não há prova de subscrição ou disponibilidade contratual por atividade.

Prioridade >=70 em um dos quatro índices exige cobertura na indicação automática, além da meta global. Assim a sexta comum não pode diluir silenciosamente uma necessidade alta. Preferência individual por patrimônio, continuidade ou terceiros multiplica por 1,5 os pesos correspondentes e registra o efeito. Não altera fatores físicos. A confiança geral continua ponderada pelos pesos efetivos.

Triagem roda antes da escolha: obra, condenação e parede combustível observadas bloqueiam o prosseguimento, e objeto básico acima de R$7,5 milhões encaminha ao produto personalizado. R$7,5 milhões exatos não excedem o corte. Valores ausentes continuam pendentes. O limite considera conteúdo + estoque médio + reconstrução quando disponíveis; não soma RC, despesas e aluguel. Endereços fictícios não alimentam classificação de comunidade, renda ou delegacia.

A edição do pacote mantém as seis obrigatórias, permite ajustar as quatro adicionais padrão no Prático/Total e recalcula sua aderência. Adicionais de operação requerem confirmação; todos permanecem solicitações condicionais à atividade e aceitação. Não são somados ao numerador das dez necessidades e não geram novos índices sem calibração. Assistências permanecem fixas. A vigência aceita inteiros de um a cinco anos. Confirmações e preferências no formulário são locais à unidade e limpas ao trocar o vínculo; as preferências globais da CLI/Streamlit continuam explicitamente globais.
