# Portal e formulário de cotação empresarial

Front-end independente, em HTML/CSS/JavaScript, com home, produto empresarial e formulário local de seis etapas. Não exige npm install nem serviços pagos.

## Executar

Requisito: Node.js 20 ou superior. Na raiz deste repositório:

```sh
cd frontend
npm run dev
```

No PowerShell, se a política bloquear npm.ps1, use `npm.cmd run dev`.

- Home: http://localhost:4174/
- Seguro Empresarial: http://localhost:4174/seguros/seguro-empresarial
- Formulário: http://localhost:4174/cotacao

O servidor atende apenas no computador local. Para usar outra porta, defina PORT; para encerrar, Ctrl+C.

## Formulário e busca

- Seis etapas: dados pessoais, empresa, endereço, planos, revisão/pagamento demonstrativo e conclusão.
- Sem campo CPF. Pessoa jurídica pode informar o CNPJ da empresa.
- 970 atividades e 1.007 vínculos de subatividade do catálogo público capturado em 28/10/2026.
- Nomes por extenso, sem cortar as opções com reticências.
- Rolar a lista, digitar ou descrever o funcionamento da empresa no mesmo controle.
- Sugestões de atividade e subatividade com confirmação do usuário.
- Busca inteligente local por termos, sinônimos, conceitos e relevância, sem modelo generativo nem chaves.
- Nenhuma informação preenchida é enviada à seguradora. Os dados do formulário ficam em memória e são apagados ao recarregar ou reiniciar.

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
