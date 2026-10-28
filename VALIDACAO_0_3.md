# Validação da integração 0.3

Executada localmente em 28/10/2026, Python 3.12. A suíte passou em **93 testes**. A configuração integra as escolhas denominadas DevD/DevM na conversa e a lógica SSP da DevC; o ZIP mvp_1 foi a referência para as cinco heurísticas comuns, meta e indispensáveis. Não pressupõe a existência de branches remotas com esses dois primeiros nomes.

## Contrato verificado

- Quatro índices multifatoriais contínuos, sem recategorização em 25/55/85 e sem multiplicar novamente pelo patrimônio.
- Nove necessidades na aderência; meta padrão 80%; menor nível que atinge a meta e inclui todas as indispensáveis.
- Exigência explícita continua valendo mesmo com nota zero e meta zero.
- Cinco heurísticas identificadas como preferências experimentais, separadas de probabilidade, dimensão financeira e índices físicos.
- Confiança por componentes, intervalos conservadores da razão de aderência e auditoria das contribuições.
- CEP/código IBGE, referências públicas e SSP usando o mesmo cruzamento municipal. SSP preserva clima/NR-4 e não deixa metadados antigos atribuídos à nova fonte.
- Templates originais, JSON de auditoria e preferências reproduzíveis na configuração do lote.
- Preços continuam pendentes; nenhuma cotação foi inventada.

## Bases completas

Processamento com configuração padrão, sem indispensáveis, usando os snapshots públicos disponíveis. Nenhuma fonte SSP real foi fabricada ou adicionada aos snapshots durante esta atualização.

| Resultado | Desenvolvimento | Teste comum |
|---|---:|---:|
| Estabelecimentos | 2.978 | 144 |
| Essencial | 71 | 2 |
| Prático | 2.852 | 136 |
| Total | 55 | 6 |
| Linhas de coberturas | 20.814 | 1.016 |

Verificados unicidade dos pares empresa/unidade e empresa/unidade/cobertura, quantidade de registros, correspondência das coberturas ao plano e preferências no manifesto. Saídas locais ignoradas pelo Git em output/integracao_0_3_desenvolvimento e output/integracao_0_3_teste. A distribuição mudou devido à nova regra de aderência; não comprova qualidade preditiva ou adequação comercial.

## SSP

Testes usam planilhas XLSX sintéticas e simulação de download, sem consultar portais reais. Foram verificados leitura de números sem alterar ordem de grandeza; soma das regiões antes da divisão; ausência preservada; denominador ausente; doze meses e total; regiões duplicadas/sobrepostas; seleção de um ano; escala fixa independente do subconjunto; cache e atualização deliberada; hashes, fonte e vínculo municipal no motor e no CEP. Um SSP local isolado não esconde os snapshots distribuídos de clima/NR-4.

O importador está integrado. Alimentação real exige manifesto com planilha/URL compatível, denominador do mesmo período e confirmação de abrangência sem sobreposição. Não há descoberta de todos os portais nem atualização agendada. A escala SSP inicial é uma hipótese a calibrar; contagem de ocorrências não é probabilidade. Nenhuma taxa foi estimada a partir de dados faltantes.

## Interface

Verificado no navegador local: empresa de exemplo sugerida como Prático com meta 80%; marcar Quebra de vidros como indispensável muda para Total e preserva as quatro notas. A suíte também verifica essa preferência no ZIP exportado. Captura demonstrativa em output/integracao-0-3.png.

Consistência computacional não substitui calibração atuarial, análise contratual ou revisão das definições das fontes.
