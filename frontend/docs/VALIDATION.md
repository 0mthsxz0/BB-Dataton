# Verificação da entrega

Data: 27/10/2026. Navegador integrado do Codex, servidor local Node.

## Resultado

- `npm.cmd run check`: passou para `public/app.js` e `server.mjs`.
- 18 checagens funcionais de navegador: 18 passaram, zero falhas no registro final.
- Nenhum erro de console retornado nas ações examinadas.
- Sete verificações HTTP: seis respostas 200 para páginas/assets e 404 para arquivo inexistente.
- Catálogo: três planos, 13 coberturas, 42 assistências e zero referências a IDs inexistentes.
- Layout inspecionado em desktop e em larguras de 390 px e 360 px. A checagem final em 390 px retornou largura de documento de 375 px para viewport de 390 px; em desktop, 1.265 px para viewport de 1.280 px. A tabela e o blog mantêm rolagem dentro dos próprios contêineres.

## Checagens funcionais registradas

| Caso | Resultado |
| --- | --- |
| Troca para o Essencial atualiza o preço do resumo | PASS |
| Busca filtra a cobertura de vendaval | PASS |
| Busca inexistente informa ausência de resultados | PASS |
| Alternância para a aba de assistências | PASS |
| Busca de eletricista retorna a assistência | PASS |
| Modal da descrição abre | PASS |
| Primeira pergunta do FAQ expande | PASS |
| Setas navegam entre as abas | PASS |
| Marca navega para a home | PASS |
| Filtro de empresas retorna o produto empresarial | PASS |
| Busca vazia de produtos exibe mensagem | PASS |
| Carrossel de destaques avança | PASS |
| Busca global filtra o produto empresarial | PASS |
| Resultado global navega para a página empresarial | PASS |
| Menu móvel expande com estado acessível | PASS |
| Preferência de cookies persiste após recarga | PASS |
| Plano Total abre com ID 894 selecionado | PASS |
| Escape fecha o modal | PASS |

Evidências copiadas para `docs/evidence/browser-checks.json` e `docs/evidence/http-data-checks.json`. As checagens de geometria, dez produtos e doze artigos também foram observadas diretamente na sessão de navegador. As capturas estão em `docs/screenshots/`.

## Correções feitas durante a revisão

- Corrigida a resolução do diretório público no servidor Windows.
- Corrigida a altura da imagem para respeitar o dimensionamento responsivo.
- Corrigida a posição dos rótulos visualmente ocultos dos links, que causava transbordamento horizontal no carrossel do blog.

## Limites da validação

Esta é uma verificação funcional e visual, sem promessa de equivalência integral com o portal. Não houve comparação automatizada pixel a pixel, auditoria WCAG completa, testes em dispositivos físicos, testes de contratação, autenticação, emissão ou precificação. Os destinos externos foram identificados por seus links; não foram submetidos formulários ou dados de usuário.

O REA produziu análise estática focada com sucesso, mas a cobertura do portal permanece parcial. O relatório de investigação detalha o timeout do bundle maior, o escopo selecionado e os limites semânticos.
