# Formulário de cotação e busca de atividades

## Consulta municipal de segurança

Na branch `dados-de-seguranca`, a etapa de endereço permite consultar o índice
municipal pelo servidor local. Somente cidade/UF e, depois, o código IBGE são
enviados nessa consulta; dados pessoais e o endereço completo continuam na página.
O resultado mostra período, faixa, situação do dado e fontes. Banco ausente ou
dados insuficientes aparecem como indisponibilidade, sem risco presumido.
O cenário de necessidade usa valor dos bens, garagem e uso, com multiplicadores
explicitamente hipotéticos. Consulte [a metodologia e o estado da coleta](../../docs/DADOS_DE_SEGURANCA.md).
As afirmações históricas abaixo sobre ausência de requisições se referem à versão
original do formulário; a consulta municipal local é a adição descrita nesta seção.

## Entrega em 28/10/2026

A pasta `frontend/` reúne a home e a página empresarial da etapa anterior e um fluxo local em seis etapas:

1. Dados pessoais: pessoa física ou jurídica, nome/razão social, nascimento e estado civil quando aplicáveis, celular e e-mail. **Não existe campo CPF.** Para pessoa jurídica, permanece o CNPJ da empresa.
2. Empresa: atividade econômica, subatividade, proteção de imóvel/conteúdo e localização em shopping center.
3. Endereço do estabelecimento.
4. Escolha entre Essencial, Prático e Total, com valores de referência identificados.
5. Revisão e preferência demonstrativa de pagamento.
6. Conclusão local e download de resumo sem dados pessoais.

Os CTAs da home e da página empresarial levam a `/cotacao`. A escolha prévia de um plano é preservada durante a navegação. Não há requisições com os dados preenchidos; estado pessoal e descrição livre ficam somente na memória da página. Recarregar ou reiniciar limpa essas informações. A preferência de cookies existente no portal usa apenas armazenamento local.

## Três maneiras no mesmo controle

- Abrir e rolar a lista completa, ordenada pelo nome por extenso.
- Digitar parte do nome, com normalização de acentos, busca por termos e aproximação para pequenas diferenças de escrita.
- Abrir “Busca inteligente” e descrever o funcionamento do negócio. A descrição retorna até três sugestões, com uma explicação e subatividade quando existe uma candidata suficiente.

A interface não usa reticências para cortar os nomes das opções. A atividade confirmada aparece também em um bloco com quebra de linha. Trocar de atividade descarta a subatividade anterior, a menos que uma nova escolha compatível tenha sido confirmada.

O catálogo é completo para o snapshot coletado: 970 atividades, 1.007 relações e dez atividades sem subatividade retornada. Essas dez permitem descrição manual para confirmação posterior. Os dados e a origem estão em `catalog-source/README.md`.

## Como funciona a busca inteligente

O motor em `public/activity-search.js` é **local e determinístico**. Usa termos normalizados, pesos por raridade, prefixos, similaridade de trigramas para nomes, sinônimos e conceitos de segmentos. Considera diferenças entre fabricação, varejo, atacado e reparação, inclusive negações comuns. Não usa um modelo generativo ou embeddings; não exige chave, pacote adicional ou serviço pago.

Exemplos cobertos nos testes: refeições/pizza, beleza, vestuário no varejo, móveis de madeira, assistência de computadores, software sob encomenda, mercearia, odontologia, contabilidade e lavanderia. Isso não representa cobertura exaustiva de toda linguagem natural.

O motor retorna somente opções existentes no catálogo. Sugestões não alteram o formulário até que o usuário as confirme. Subatividade única é apresentada como a única relação da fonte, não como evidência semântica de que o negócio foi compreendido. Quando há várias subatividades sem diferença suficiente de pontuação, o usuário escolhe. Entradas vagas pedem esclarecimento em vez de aceitar a primeira opção da lista.

As explicações de correspondência não são probabilidades, laudos ou decisões de aceitação de seguro. A interface não decide elegibilidade, prêmio, limites de indenização ou aprovação contratual.

## Evidência da página original

Página e bundle público consultados:

- https://cotacaoseguroempresarial.bbseguros.com.br/home
- `/static/js/main.4c90cfed.js`
- `/static/css/main.eddc160d.css`

O HTML referencia uma aplicação React. Os campos das três primeiras etapas foram identificados no DOM, inclusive os painéis ocultos, e no bundle público:

- Os títulos das etapas aparecem próximos do deslocamento de caractere 347.683.
- Os nomes dos campos econômicos constam no módulo 6723: `atividadeEconomicaBb`, `atividadeEconomica`, `objetoDoSeguro`, `localizadaEmShopping`, `subatividadeDesc`.
- O carregamento de subatividades e a limpeza da seleção anterior aparecem no componente `Je`, próximo do deslocamento 339.388.
- O módulo 3617 descreve os seis segmentos: razão social, dados da empresa, dados do imóvel, planos, cadastro e pagamento, sucesso.
- As rotas identificadas são `/home`, `/planos`, `/contratacao`, `/resumo-proposta`, `/proposta` e `/finalizar`, além das rotas de autenticação.

Esses deslocamentos referem-se ao bundle retido localmente no workspace, decodificado em UTF-8. O código proprietário foi usado somente como evidência, não é executado pelo protótipo e não foi incluído no repositório.

O REA 6.8.0 também foi executado sobre um recorte inerte de 4.892 bytes do componente de atividade: um arquivo analisado, 1.583 nós AST visitados e zero falhas de parsing. O resultado é parcial por seleção de escopo e referências externas ao recorte; não prova entendimento integral da SPA. O resumo e os limites estão em `docs/evidence/rea-form-summary.json`.

## Diferenças e limites

Os seis segmentos de navegação estão implementados como demonstração. A interface não é uma reprodução integral dos fluxos autenticados de contratação. Cadastro de usuário, senha, documentos de beneficiários, dados reais de cartão/conta, termos contratuais, questionários dependentes de cotação e emissão de proposta não foram reconstruídos como serviços funcionais. A etapa de pagamento demonstra a escolha da modalidade, parcelas e dia; as opções não são condições comerciais garantidas.

Não foi enviada uma cotação fictícia à produção para observar as respostas posteriores. Os passos iniciais foram confirmados por DOM/código; os passos finais são uma adaptação demonstrativa dos segmentos identificados. Preços não são calculados a partir dos dados informados. O site explicita isso antes da seleção e da conclusão.

O layout mantém a referência de cabeçalho amarelo, imagem lateral, campos contornados e progresso. A fotografia e os ícones são próprios; a fonte é uma aproximação local. A autenticação anônima usada na coleta não é usada pelo front-end em execução.

## Validação

- 18 testes Node passam para integridade do catálogo, expansões principais, descrições de segmentos, busca aproximada, entradas vagas, negação e vínculo de subatividades.
- Sintaxe verificada para servidor, portal, formulário e mecanismo de busca.
- Fluxo de seis etapas percorrido no navegador local com dados de demonstração.
- Lista de 970 atividades, seleção por teclado e mudança de atividade/subatividade examinadas no navegador.
- Layout pessoal e busca inteligente examinados em 390 px, sem transbordamento horizontal.
- Nenhum erro de console retornado nas ações testadas.

Os testes estão em `tests/activity-search.test.js`. Capturas em `docs/screenshots/cotacao-*.jpg` e relatório de checagens em `docs/evidence/cotacao-browser-checks.json`.
