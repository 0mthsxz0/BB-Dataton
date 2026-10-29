# Recuperação das jornadas — 29/10/2026

A investigação comparou a `main` executada em `C:\PROJETOS\BB-Dataton` com as cópias locais `BB-Dataton/frontend` e `.analise-integracao`, além do histórico Git. Não havia uma única versão completa desaparecida: havia recursos já publicados que ficaram fora do caminho por ID e melhorias ainda sem commit em outras cópias.

## Origem da diferença

| Parte | Evidência encontrada | Integração na main |
| --- | --- | --- |
| Relatório simples do cliente | `f0b7488` separou as jornadas; `e6c0b9f` unificou o pacote. Esses recursos já estavam no histórico. | Resposta rápida por ID também usa a apresentação do cliente, com lista de proteções e resumo baixável. |
| Consulta por ID exibindo relatório técnico | `1e9d97c` introduziu `cadastroRecommendationView(demoResult.relatorio)` no fluxo público. | O relatório técnico continua no painel interno; o cliente recebe `customerRecommendationView`. |
| Modal no lugar de continuação da jornada | `153d2ff` adicionou o editor de confiança; `029b0ee` integrou esse editor à main, inclusive na consulta demonstrativa. | O cliente recebe “Refinar a resposta”, com continuação no formulário existente. O editor do colaborador permanece disponível. |
| Refinamento por ID | Alterações locais ainda sem commit em `.analise-integracao/frontend/public/id-journey.js` e `quote.js`. Essa cópia também contém um experimento de outra metodologia. | Recuperado o comportamento de continuação, com adaptação ao motor atual: manter empresa/unidade, aproveitar valores e confirmações disponíveis e recalcular na rota local de demonstração. |
| Opcionais no pacote | `opcionais.py`, `produto.py` e `product-ui.js` já implementavam sugestões, confirmação e composição automática. | A resposta inicial apresenta as proteções pertinentes em um único pacote sugerido, sujeito às confirmações indicadas. Confirmações no formulário adicionam as proteções compatíveis ao pacote unificado; exclusões continuam respeitadas. Modalidades de lucro são agrupadas na sugestão inicial e seguem escolha exclusiva no pacote. |
| Confiança no resumo simples | Cópia local `BB-Dataton/frontend/public/journeys.js` e teste correspondente. | Indicador compacto acompanha o resultado atual, sem expor as contas e tabelas internas. |
| Busca de atividades v3 | Arquivos locais `activity-search.js`, `activity-vocabulary.js`, `activity-metrics.js`, refinamento na interface e conjunto de avaliação. | Recuperados sinônimos, negação, perguntas estruturadas, distinção entre agência e concessionária, invalidação de sugestões antigas e opção de busca local. Mantidas autenticação, voz e integrações da main. |

O experimento Mosler de `.analise-integracao` foi preservado na cópia original. Ele altera metodologia de cálculo e exportações; não é necessário para recuperar a experiência de cliente e não foi tratado como uma substituição automática do motor da main. Arquivos antigos de servidor também não foram copiados por inteiro, pois não continham as proteções e integrações mais recentes.

## Verificação

- 320 testes Python passaram.
- 75 testes Node passaram, incluindo a busca recuperada, os dois tipos de relatório, preenchimento por ID e bloqueio da rota demonstrativa quando desabilitada.
- Avaliação de desenvolvimento: 200 variações sintéticas, 200 acertos no primeiro resultado e nenhum identificador inválido. Esse conjunto não mede generalização para clientes reais.
- Consulta e refinamento HTTP com base local: mesma empresa/unidade, três opcionais confirmados incluídos e plano compatível. Evidência sanitizada em `frontend/docs/evidence/recuperacao-jornadas.json`.
- Navegador: consulta por ID, seleção de unidade, resumo simples, refinamento, valores disponíveis recolhidos para revisão e recálculo com Delivery, refrigeração e eletrônicos incluídos no pacote.
- Captura do resultado: `frontend/docs/screenshots/cliente-recuperado.png`.

Os CSVs, configurações privadas, senhas e cópias de segurança locais não fazem parte da publicação.
