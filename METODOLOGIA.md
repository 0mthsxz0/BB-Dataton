# Metodologia do motor multifatorial

## 1. Contrato do modelo

A saída principal é prioridade de proteção (0–100), não probabilidade de sinistro. Para cada cobertura, o sistema também devolve indicador relativo do evento (R), impacto normalizado (I), vulnerabilidade limitada pelos dados (V), confiança, valores de cenário, explicações e sensibilidade.

Todos os pesos são hipóteses iniciais da equipe; não são parâmetros oficiais da BB Seguros. Sem histórico de sinistros e exposição por período, não é possível demonstrar calibração atuarial ou estimar perda anual esperada. O produto entre um índice relativo e patrimônio não é tratado como perda esperada em reais.

## 2. Unidade de análise e patrimônio

Uma linha por `(empresa_id, imovel_id)`. Bens são agregados antes das junções. Cruzamentos validam relações muitos-para-um/um-para-um, chaves e vínculos. Registros de bens exatamente repetidos são deduplicados; conflitos de identificação são rejeitados.

```
B_ponderado = soma(valor_cadastrado × probabilidade_bem_no_imovel_referencia)
E_central = B_ponderado + estoque_medio_estimado
E_alternativo = B_total_referencia + max(estoque_medio, estoque_pico)
```

O valor ponderado é recalculado: não se multiplica novamente `valor_bem_ponderado_referencia`, que pode conter arredondamentos. A probabilidade de localização distribui patrimônio; não representa sinistro. Os bens das unidades sem cadastro são desconhecidos, não comprovadamente inexistentes. Vínculos inválidos reduzem a completude. O cenário integral é exploratório, não confirma a presença de todos os bens.

Estoque médio e pico são alternativas, nunca somados. Confirmar sobreposição e quais bens são suscetíveis à perda do evento e contratualmente cobertos. A primeira versão não estima a fração roubável de cada bem, valor de reconstrução do prédio ou custo de reposição a partir do preço cadastrado.

## 3. Impacto financeiro

Para valores monetários observados:

```
I = clip[ln(1 + E/s) / ln(1 + E_ref/s), 0, 1]
```

`s = R$ 10.000` é a escala inicial; `E_ref` depende da cobertura. Referências iniciais: R$ 3 milhões para conteúdo em incêndio/roubo/vendaval; R$ 1 milhão para equipamentos; R$ 300 mil para cenário de aluguel; R$ 1,5 milhão para despesas de paralisação; R$ 1 milhão para cenário digital parcial.

Justificativa: comprimir diferenças de ordens de grandeza sem fazer uma média entre dinheiro e índices. Esses valores organizam a escala do protótipo; precisam de revisão e análise de sensibilidade. Não são limites oficiais, cotação ou importância segurada recomendada por contrato. O valor bruto permanece visível acima da saturação.

Não há ajuste automático por lote: o desenvolvimento e o teste usam as mesmas referências. Não se ajusta o modelo usando a distribuição do teste.

## 4. Indicador do evento

`R = soma(peso_j × fator_j)`. A combinação ponderada ocorre dentro da dimensão do evento. A prioridade final não é média dos componentes: inclui multiplicação e interações.

| Cobertura | Indicadores e pesos iniciais de R | Impacto e limitações |
|---|---|---|
| Incêndio | Atividade 50%, material 30%, padrão 20% | Bens/estoque; equipamento de cozinha observado acrescenta interação. Não presume cozinha pela atividade. |
| Danos elétricos | Despesa de energia 60%, atividade 40% | Equipamentos elétricos; dependência digital aumenta a consequência operacional. Energia não prova falha. |
| Aluguel | Atividade 60%, material 40% | Aluguel observado × cenário de paralisação. Relação locador/inquilino e aplicação contratual a confirmar. |
| RC estabelecimento | Atividade 70%, sinal de loja 30% | Impacto financeiro desconhecido; não reutiliza atividade como valor de indenização. |
| Despesas fixas | Atividade 40%, dependência digital 30%, material 30% | Despesa agregada × cenário; sem somar novamente folha/aluguel. |
| Roubo | Exposição territorial 100% | Patrimônio exposto; sem colocar patrimônio no componente do evento. |
| Vendaval | Clima 70%, padrão 30% | Conteúdo cadastrado. Sem clima externo, fator climático ausente e confiança baixa. |
| RC empregador | Atividade 70%, funcionários 30% | Folha normalizada apenas como proxy de porte da exposição; não vira indenização. Funcionários são do nível da empresa. |
| Vidros | Sinal de loja/galeria 65%, atividade 35% | Impacto desconhecido; confirmação necessária. Área não comprova vidraças. |
| Cibernética adicional | Indicador de tratamento de dados 100% | Cenário parcial de custos de interrupção proporcional à dependência digital e bens de informática. Não mede ataque nem controles. |

As variáveis da dimensão do evento são proxies contextuais e hipóteses, não frequências observadas. Pesos maiores indicam maior influência pretendida na triagem, sem alegar associação empírica comprovada. Os mapas por atividade e construção estão no JSON e ficam visíveis na auditoria.

A primeira versão usa um representante por fenômeno digital: dependência digital e tratamento de dados, evitando somar todos os índices derivados correlacionados. Os demais campos permanecem na base para revisão futura. Maturidade digital e equipamentos de segurança cadastrados não reduzem a exposição sem evidência dos controles técnicos/funcionamento.

## 5. Vulnerabilidade

Na ausência de caixa, reservas e custos de recuperação, o modelo usa uma proxy limitada:

```
V = clip(despesa_fixa_mensal_da_unidade / faturamento_mensal_da_empresa, 0, 1)
```

Aplicada somente a empresa de uma unidade. A confiança dessa proxy é limitada a 0,40. Não representa liquidez ou solvência. Para múltiplas unidades ou receita/despesas ausentes, o ponto central é a hipótese configurada (0,50), com confiança zero e sensibilidade ampla. Faturamento não é distribuído arbitrariamente entre unidades.

## 6. Prioridade e interações

```
P = 100 × clip[I × (a + (1-a)R) × (b + (1-b)V) + k × I × R × D, 0, 1]
```

Parâmetros iniciais: `a = 0,65`, `b = 0,70`. O componente do evento pode reduzir a parcela multiplicativa até 35%, mantendo um piso de atenção à severidade; a vulnerabilidade pode modulá-la até 30%. Esses pisos são preferências de decisão do protótipo para não anular perdas elevadas. Não representam risco residual de 65%/70% nem probabilidades mínimas de evento.

`D` descreve uma interação específica. `k` varia de 0 a 0,15: cozinha 0,12; dependência digital 0,15; comprometimento de custos 0,10–0,12; presença física 0,10; trabalhadores/atividade 0,12. Roubo e vendaval não têm interação adicional além da multiplicação dos componentes.

Os coeficientes limitam o efeito adicional a no máximo 15 pontos. Sua justificativa inicial é impedir que uma proxy isolada domine a decisão. O efeito real depende dos produtos entre fatores. O sistema exporta base, interação e efeito da limitação a 100, permitindo reconstruir a nota.

Aumentar patrimônio mantém R de roubo constante e aumenta I até a saturação. Segurança territorial relativa máxima não zera P quando há impacto. Reduções de R, V ou D reduzem a prioridade mantendo os outros fatores, dentro dos pisos. Dados ausentes não são automaticamente fatores protetores.

Classes iniciais: [0,25) muito baixa; [25,50) baixa; [50,70) moderada; [70,85) alta; [85,100] muito alta.

## 7. Ausências, confiança e sensibilidade

Fatores ausentes usam ponto central 0,50 e confiança zero. O ponto central do evento totalmente ausente e da vulnerabilidade ausente é configurável. Categoria não reconhecida é desconhecida, não risco zero. Valor negativo/não finito é inválido. Zero cadastrado pode ser observado, mas ausência de aluguel não prova propriedade.

Confiança do resultado = média da confiança do evento, impacto e vulnerabilidade. Trata-se de qualidade relativa da evidência, não probabilidade de acerto. A confiança do evento pondera a qualidade dos fatores. A confiança dos bens considera completude da ponderação e vínculos de baixa confiança. Todos os valores são hipóteses explícitas da equipe.

Para um fator x com confiança c, a sensibilidade é explorada de `x×c` a `x+(1-c)×(1-x)`. O motor propaga extremos dos componentes não negativos. É uma faixa de sensibilidade à evidência incompleta, não intervalo de confiança estatístico. A confiança não multiplica a prioridade final para transformá-la em falsa baixa necessidade.

## 8. Seleção de plano

O catálogo é lido do CSV. Essencial é a base. Cada candidato é comparado ao escolhido até então. Calculam-se adequação relativa, contribuição das novas coberturas e lacunas importantes.

```
adequação = soma(peso_c × prioridade_c coberta) / soma(peso_c × prioridade_c total)
ganho = soma(peso_c × prioridade_c nova) / soma(peso_c × prioridade_c total)
```

Pesos iniciais das coberturas = 1. Upgrade quando acrescenta cobertura com nota ≥60 e ganho ≥15%, ou resolve uma lacuna crítica ≥85. Entre alternativas que atendem ao critério, o processamento mantém o menor plano suficiente. Coberturas comuns nunca justificam upgrade sozinhas. Os limiares são hipóteses de decisão e não devem ser calibrados para selecionar uma fração desejada da base.

O algoritmo também avalia as faixas inferior/superior para sinalizar instabilidade da recomendação. Não otimiza custo, margem ou acessibilidade sem cotação. A análise de preço sempre permanece pendente.

## 9. Elegibilidade e valores sugeridos

Regras preliminares baseadas no guia do desafio: material combustível, obra/situação cadastral e vínculo do endereço geram confirmação. Não existe tabela de aceitação oficial por CNAE no pacote; aceitação de atividade e regras contratuais são pendentes por padrão. O motor não transforma hipóteses em exclusões oficiais. Plano sugerido é condicional; a exportação registra as pendências.

Faixas patrimoniais usam cenários de bens/estoque; elétricos usam equipamentos. Aluguel e despesas usam 1 a 3 meses inicialmente, configuráveis e sem presumir duração média do sinistro. São referências de exposição para discutir dimensionamento, sem valores de franquia, limite aprovado ou preço de seguro. O cenário de incêndio não cobre silenciosamente prédio sem valor de reconstrução.

RC estabelecimento/empregador e vidros exigem estimativa adicional para faixa monetária defensável. O sistema justifica a ausência em vez de multiplicar faturamento, folha ou área por constantes sem fundamento. Cibernética fica na auditoria como avaliação adicional; não é exportada como cobertura fixa/disponível.

## 10. Validação e próximos dados

Testes verificam contraste de R$30 mil/R$3 milhões na mesma cidade; monotonicidade; proteção não anulada por segurança relativa; equipamentos; dependência digital; sinais de loja; maturidade não interpretada como vulnerabilidade; unidades independentes; confiança; duplicações; exportação e estabilidade.

Aceitação desta versão: todas as unidades processadas, nove notas fixas + uma adicional, cálculos finitos e reconstruíveis, colunas dos templates preservadas, vínculos validados, cenários documentados e nenhuma probabilidade de sinistro ou preço inventado.

Próxima validação substantiva: revisão dos mapas e coeficientes com especialistas, sensibilidade das referências e limiares, valores de reposição, inventário de vidros, segurança em funcionamento, reservas/caixa, aceitação contratual e histórico de sinistros com períodos de exposição. Casos contrastantes validam coerência lógica, não precisão preditiva.
