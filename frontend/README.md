# Portal e formulário de cotação empresarial

Portal em HTML/CSS/JavaScript, com formulário de sete etapas integrado ao motor Python do MVP. Não exige npm install, chave de IA ou serviço pago.

## Executar

Requisitos: Node.js 20+ e Python 3.12/3.13 com as dependências do projeto. Na raiz:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd --prefix frontend run dev
```

No PowerShell, se a política bloquear npm.ps1, use `npm.cmd run dev`.

- Home: http://localhost:4174/
- Seguro Empresarial: http://localhost:4174/seguros/seguro-empresarial
- Formulário: http://localhost:4174/cotacao

O servidor atende apenas no computador local. Para usar outra porta, defina PORT; para encerrar, Ctrl+C.

O servidor detecta `.venv` automaticamente. Para outro interpretador, configure `BB_PYTHON` com o caminho do executável. Os CSVs seguem a descoberta do MVP (pasta `data/desenvolvimento` ou `Seguro_Empresarial_Desenvolvimento` ao lado do repositório). Sem base local, o formulário usa os valores declarados e mantém as ausências explícitas. Os dados do Datathon são de demonstração; não há conexão com o BB de produção.

## Formulário e busca

- Sete etapas: dados pessoais, empresa, endereço, proteção, planos, revisão/pagamento demonstrativo e conclusão.
- Sem campo CPF. Pessoa jurídica pode informar o CNPJ da empresa.
- 970 atividades e 1.007 vínculos de subatividade do catálogo público capturado em 28/10/2026.
- Nomes por extenso, sem cortar as opções com reticências.
- Rolar a lista, digitar ou descrever o funcionamento da empresa no mesmo controle.
- Sugestões de atividade e subatividade com confirmação do usuário.
- Busca inteligente local por termos, sinônimos, conceitos e relevância, sem modelo generativo nem chaves.
- API local de busca com validação de atividade e subatividade reais.
- Vínculo opcional com um estabelecimento da base; os valores declarados substituem os respectivos agregados do cadastro.
- Selecionar o estabelecimento já exibe o plano sugerido e uma explicação detalhada na mesma etapa, usando o motor original e sem presumir respostas. A explicação inclui dados cadastrais, memória dos índices, pesos e comparação dos três planos.
- Oito perguntas obrigatórias, duas para cada índice. Resultados, origem dos dados, fontes, confiança e comparação dos planos são calculados pelo motor Python.
- Contatos e pagamento ficam no navegador. Somente dados de proteção são enviados ao servidor local; a descrição vai à API local de busca. Nada é enviado à seguradora ou a uma API de IA.
- Consulta da cidade/UF à API do IBGE e uso de referências públicas municipais versionadas. Importação SSP disponível pelo fluxo documentado.

Fórmulas, perguntas, contratos das APIs, limitações e integração SSP: [INTEGRACAO_MVP.md](docs/INTEGRACAO_MVP.md).

O fluxo anterior da home e do produto também está incluído: filtros de seguros, comparação pesquisável de coberturas/assistências, benefícios, FAQ, blog e navegação responsiva.

## Verificar

```sh
npm run check
npm test
```

Os 18 testes verificam a integridade do catálogo, descrições de segmentos, nomes aproximados, entrada vaga, negação e subatividades compatíveis. As checagens de navegador estão documentadas em [COTACAO.md](docs/COTACAO.md).

## Documentação

- [Formulário, busca, fontes e limites](docs/COTACAO.md)
- [Proveniência do catálogo](catalog-source/README.md)
- [Investigação anterior do portal](docs/INVESTIGATION.md)
- [Especificação anterior do portal](docs/CLONE_SPEC.md)
- [Verificação anterior](docs/VALIDATION.md)
- [Imagem própria e prompt](docs/ASSETS.md)

Os relatórios anteriores são o registro da primeira entrega, em 27/10/2026. COTACAO.md descreve a versão atual, incluindo a substituição do modal inicial pelo formulário completo.

Para reconstruir o catálogo a partir dos snapshots, na raiz do repositório:

```sh
python scripts/preparar_catalogo_cotacao.py
```

## Limites

É um protótipo de interface sem vínculo institucional, emissão de seguro, autenticação na seguradora, análise de elegibilidade ou precificação. A etapa de pagamento é demonstrativa e não recebe dados de cartão/conta. Preços são referências públicas da consulta anterior; a contratação válida ocorre no canal oficial. Campos e fluxos dependentes de respostas reais de cotação não foram tratados como serviços disponíveis.

O motor Python do datathon permanece separado deste front-end. Os CSVs da organização não são publicados ou carregados pelo site.


Atualização do item 10: veja [GUIA_ATUALIZADO.md](docs/GUIA_ATUALIZADO.md). Matriz do desafio 6/8/10, cobertura cibernética obrigatória, triagem e composição personalizada implementadas na versão 0.4.

## Jornadas de prospecção

A landing page leva a `/cotacao`: cadastro próprio, sem consulta de empresas, recomendação simples e resumo sem índices ou rastreabilidade. `/interno` abre o painel de prospecção ativa a partir da seleção de estabelecimento, com fontes, dados e justificativas técnicas. Os dois fluxos usam o mesmo motor Python e recalculam a escolha do plano. O painel interno é local e demonstrativo: requer autenticação e autorização de servidor antes de publicação. O cadastro é mantido em memória durante a sessão, sem persistência de leads.
