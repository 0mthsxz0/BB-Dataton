# Investigação do front-end

Consulta: 27/10/2026, fuso America/Sao_Paulo.

## Fontes e uso efetivo

| Fonte | Aplicação neste trabalho |
| --- | --- |
| [JoasASantos/REA-Prompts](https://github.com/JoasASantos/REA-Prompts) | Lidos os packs 04, 11, 16 e 20. Aplicados: reconstrução por comportamento, rastreamento de funcionalidades, separação entre fatos e hipóteses, registro de divergências. Checkout `ccb02b89721dd7d466beb17004a89d6bc25f5b02`, em `.rea/references/REA-Prompts`. |
| [morluto/rea](https://github.com/morluto/rea) | Executado o CLI oficial `rea-agents@6.8.0` sobre dois bundles públicos retidos localmente. Consultadas a documentação CLI e a documentação de workflows JavaScript. |
| [NUDelta/Unravel](https://github.com/NUDelta/Unravel) | Referência complementar de engenharia reversa web para relacionar interações, mudanças de DOM e bibliotecas. README consultado; extensão não instalada nem executada. |
| [Made with REA — prompts](https://madewithrea.com/prompts) | Referência complementar para mapeamento de uma funcionalidade web por vez e reconstrução independente. |
| [Home BB Seguros](https://www.bbseguros.com.br/) | Observação visual e do DOM, navegação e links públicos. |
| [Seguro Empresarial](https://www.bbseguros.com.br/seguros/seguro-empresarial) | Observação visual, interações de FAQ, tipografia computada, HTML público, estado inicial e bundles. |

Não foi instalado um MCP global nem alterada a configuração do Codex. O REA foi usado por CLI a partir do cache do npm. Os bundles foram analisados como texto; não foram executados localmente.

## Evidências retidas

Os caminhos abaixo são relativos à raiz do workspace, acima da pasta do front-end.

| Evidência | Conteúdo |
| --- | --- |
| `.rea/evidence/empresarial.html` | HTML da página de produto. |
| `.rea/evidence/empresarial-dom.txt` | DOM renderizado, incluindo FAQ aberto durante a investigação. |
| `.rea/evidence/home-dom.txt` | DOM renderizado da página inicial. |
| `.rea/evidence/initial-states.json` | Estados JSON dos componentes de resumo e comparação. |
| `.rea/evidence/manifest.json` | URLs, tamanhos e SHA-256 dos dois bundles públicos. |
| `.rea/evidence/javascript/` | Bundles públicos originais, somente para análise. |
| `.rea/evidence/rea-focused-analysis.json` | Pacote de Evidence produzido pelo REA. |
| `.rea/evidence/rea-focused-summary.json` | Resumo da análise focada. |
| `.rea/evidence/rea-summary-supported.json` | Resultado parcial da análise ampla que atingiu o timeout. |
| `.rea/evidence/screenshots/` | Capturas do protótipo em desktop e celular. |

O download HTTP simples da home retornou uma página de proteção de aproximadamente 1 KB. Esse arquivo, `.rea/evidence/home.html`, não representa o conteúdo da home; o DOM renderizado e a observação no navegador foram usados como evidência. Não foi contornada a proteção.

## Fatos confirmados

1. **CMS:** o HTML empresarial declara `Generator: Drupal 10`. Isso confirma a tecnologia declarada, sem determinar a versão exata instalada.
2. **Tema:** o documento carrega recursos de `/themes/custom/bbseg/`, além de Bootstrap, Slick e recursos de jQuery/Drupal. Isso prova inclusão de recursos; não prova que todas as funções dessas bibliotecas foram usadas nas interações examinadas.
3. **Tipografia:** o estilo computado do título empresarial usa `BancoDoBrasilTitulos`, peso 700, 42 px / 46 px. Os títulos de seções usam 36 px. O azul observado é `rgb(90, 111, 255)`.
4. **Estado dos planos:** o HTML inclui `react-app-resumo-initial-state` e `react-app-tabela-initial-state`, além dos contêineres `react-app-resumo` e `react-app`.
5. **Montagem:** o bundle `public-bundle-0.js` lê esses scripts JSON com `JSON.parse`. Referências estáticas: linha 233, deslocamento de caractere 1.445.822 para o resumo; linha 235, deslocamento 1.698.613 para a tabela. Os deslocamentos referem-se ao texto UTF-8 decodificado retido, não ao arquivo original do servidor em outra versão.
6. **FAQ:** linha 221 do mesmo bundle contém `Drupal.behaviors.bbseg_faq`, o seletor `.views-field-field-pergunta` e a classe `open`. Clicar na primeira pergunta fez aparecer a resposta no DOM observado.
7. **Cotação:** o CTA aponta para `https://cotacaoseguroempresarial.bbseguros.com.br/`; os planos apontam para `/home` nesse subdomínio. A emissão da cotação não ocorre na página de apresentação.
8. **Rotas:** a home e o produto possuem menus diferentes. A home inclui Seguros, Previdência, Capitalização e Planos Odontológicos; o produto inclui Pra Você, Para Empresas, Para o Rural e Central de Ajuda.

## Dados dos planos e inconsistências observadas

| Plano | Mensalidade exibida | Contador de coberturas | IDs associados no JSON | Contador de assistências | IDs de assistências |
| --- | --- | --- | --- | --- | --- |
| Essencial | R$ 28,33 | 5 | 9 | 9 | 9 |
| Prático | R$ 34,13 | 7 | 11 | 31 | 17 |
| Total | R$ 43,48 | 9 | 13 | 40 | 42 |

O catálogo contém 13 coberturas e 42 assistências. Os campos de apresentação e os relacionamentos detalhados não têm a mesma contagem. O front-end preserva os contadores comerciais e usa os relacionamentos para montar a tabela, com uma explicação visível. Não foi inventada uma regra para reconciliar os números. Os itens “Extra” continuam identificados como tal.

## Resultado do REA

- Versão fixada: 6.8.0.
- Runtime da execução focada: Node 24.22.1 do runtime empacotado, compatível com o requisito publicado pelo pacote.
- A primeira tentativa no runtime padrão Node 26.8.2 gerou aviso de engine; foi interrompida. A execução útil foi refeita no runtime compatível.
- A análise ampla dos dois bundles atingiu o limite de 60 segundos por fonte ao processar o bundle de 1.866.325 bytes. O resultado parcial foi preservado.
- A análise focada de `public-bundle-1.js`, de 54.745 bytes, terminou com sucesso: 11.553 nós AST visitados, um arquivo JavaScript analisado e zero falhas de parsing.
- O pacote de Evidence da análise focada tem 3.607.695 bytes. Identidade do registro principal: `ev_1f1b5633b4dd690a788ecad5d1b79088ebea09633e7942cf928b3ff6276d6908`.
- A cobertura permanece **parcial**: um arquivo foi excluído do escopo focado, o limite de 1.000 nós semânticos por arquivo foi atingido e o resumo registra 2.866 desconhecidos semânticos. O sucesso do comando não significa compreensão completa do portal.

Para repetir a análise focada, com um Node compatível no PATH:

```powershell
npx.cmd -y rea-agents@6.8.0 analyze-javascript-application ".rea/evidence/javascript" --source-path public-bundle-1.js --detail summary --evidence_output ".rea/evidence/rea-focused-rerun.json" --max-semantic-nodes 1500 --max-semantic-nodes-per-file 1000 --analysis-timeout-ms 60000 --format json
```

O comando deve ser executado na raiz do workspace. Use um destino novo: REA não sobrescreve pacotes existentes. A coleta HTTP pode ser repetida com `python .rea/capture.py`; não é necessária para iniciar o front-end.

## Inferências e desconhecidos

- A separação Drupal + ilhas React é inferida da combinação de contêineres, estados iniciais, bundle e DOM. Não equivale a possuir o repositório interno.
- Regras de precificação, limites contratuais de indenização, elegibilidade, autenticação, backend, emissão, atualização de preços e respostas de APIs de cotação permanecem **UNKNOWN**.
- Não foi capturado um HAR nem executado um fluxo autenticado. URLs encontradas no HTML e no código não devem ser confundidas com chamadas observadas na rede.
- Um bundle faz referência estática a um serviço de IP externo; isso não foi reimplementado nem acionado pelo protótipo.
- As diferenças de aparência, conteúdo e comportamento estão registradas na especificação. Não se afirma equivalência integral ou fidelidade pixel a pixel.
