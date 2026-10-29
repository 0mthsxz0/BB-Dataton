# Especificação de reconstrução e melhorias

## Escopo

Protótipo local navegável da home e do Seguro Empresarial. Reconstrói a hierarquia principal e as interações de apresentação. O diretório público contém apenas a implementação própria, dados públicos selecionados e a imagem gerada para o projeto.

| Área | Comportamento observado | Implementação |
| --- | --- | --- |
| Cabeçalho | Atalhos de contratação, acionamento, assistência e menus por contexto | Menus nativos expansíveis, atalhos externos e menu móvel |
| Home | Carrossel, dez produtos, soluções, benefícios, indicadores e links institucionais | Dez produtos, três destaques próprios, filtros e busca; benefícios, indicadores e links |
| Produto | Breadcrumb, título, texto, imagem e CTA | Mesma hierarquia com imagem própria e entrada para exploração local |
| Planos | Essencial, Prático e Total, preços e contadores | Valores do snapshot e modais de detalhes por plano |
| Comparação | Grade com coberturas e assistências por plano | Grade por associações do JSON público, abas, busca e descrições em modal |
| Benefícios Premium | Câmera, Minu Biz e detector de fumaça | Três blocos, ícones próprios e links oficiais |
| FAQ | Perguntas expansíveis | Dez perguntas e respostas condensadas; acionamento nativo por teclado |
| Blog | Faixa horizontal de artigos | Doze artigos observados, navegação horizontal e links oficiais |
| Atendimento | WhatsApp e contato com especialista | WhatsApp externo e convite para explorar planos/cotação oficial |
| Rodapé | Produtos, contatos, institucional e preferências | Navegação principal, links institucionais e preferências locais |
| Cookies | Permitir, rejeitar, preferências e redefinição | Mesmas escolhas, sem instalar rastreadores; preferência em localStorage |

## Estados e transições

- **Rota:** `/` e `/seguros` mostram a home; `/seguros/seguro-empresarial` mostra o produto. Links locais atualizam a URL, as âncoras e o histórico. Recarregar diretamente uma rota deve funcionar.
- **Menu móvel:** fechado → botão de menu → aberto; botão ou Escape → fechado. `aria-expanded` acompanha o estado.
- **Menu de categoria:** resumo → lista de links; abrir outra categoria fecha a anterior.
- **Carrossel:** três índices com avanço/retorno circular e seleção direta; não existe avanço automático.
- **Busca de produtos:** público + termo → interseção dos resultados. A comparação ignora maiúsculas e acentos. Zero resultados mostra mensagem explícita.
- **Comparação:** cobertura ou assistência + termo → linhas associadas. As abas respondem a setas, Home e End. As células distinguem associação e ausência de associação com texto acessível.
- **Descrição:** item → modal com texto do catálogo; fechar ou Escape → retorna foco ao controle original.
- **Plano:** card → detalhes; explorar → seletor. Trocar seleção altera o resumo local. O link externo abre a cotação oficial em outra aba, sem transferir a seleção.
- **FAQ:** fechado → resumo → aberto; novo acionamento → fechado. Perguntas independentes permitem várias respostas abertas como melhoria de consulta.
- **Preferências:** indefinida → permitir/rejeitar/somente essenciais → persistida localmente. O rodapé reabre as escolhas. Navegadores sem armazenamento persistente continuam funcionais, mas podem reapresentar o aviso.
- **Falha no catálogo:** erro de rede ou JSON inválido → mensagem e controle de nova tentativa.

## Melhorias sobre a referência

1. Navegação por seções do produto e links diretos para a comparação.
2. Busca e filtros de público na home, com contagem de resultados.
3. Abas e busca na comparação para reduzir o tamanho da tabela exibida de uma vez.
4. Descrições de coberturas e assistências acessíveis por botão.
5. Exploração de planos sem solicitar dados pessoais.
6. Foco visível, diálogos nativos, retorno de foco, navegação por teclado e respeito a movimento reduzido.
7. Distinção entre contadores comerciais, associações do catálogo e coberturas extras.

## Diferenças deliberadas

- O código é HTML/CSS/JavaScript nativo; não é o código Drupal/React recuperado do servidor.
- Cores e hierarquia foram aproximadas visualmente. A fonte proprietária, o logo original, fotografias, ilustrações e componentes proprietários não foram incorporados.
- A imagem principal foi gerada com IA. Os ícones são próprios. Os quatro blocos de produtos financeiros/seguros adicionais usam ilustrações em vez das fotografias originais.
- As sete campanhas rotativas da home não foram copiadas. O carrossel tem três mensagens próprias e seleção manual; não replica promoções vigentes.
- Não há uma segunda versão pixel a pixel para alternar: o resultado combina a estrutura observada com as melhorias registradas.
- O blog mostra doze artigos selecionados do conjunto observado, em vez de replicar toda a listagem dinâmica.
- Textos de FAQ e descrições de produtos foram condensados. As descrições da comparação vêm do catálogo público retido.
- O contato de especialista foi substituído pela exploração de planos e link oficial, sem formulário de contato.
- Os demais produtos e serviços abrem o site oficial; não foram implementadas suas páginas internas.
- Não foram incluídos chat de terceiros, publicidade, analytics, Hand Talk, login ou serviços externos de IP. A acessibilidade nativa implementada não substitui uma avaliação completa de conformidade.

## Integração futura com o datathon

A interface pode receber uma camada separada de recomendação e explicação por empresa-estabelecimento. Essa camada exige especificar as regras, validações, contratos de dados e tratamento de incerteza. Os CSVs existentes não foram modificados, publicados nem integrados nesta entrega.
