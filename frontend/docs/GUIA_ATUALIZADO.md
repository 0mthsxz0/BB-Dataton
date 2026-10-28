# Guia aplicado ao formulário — versão 0.4

Implementação em 28/10/2026 na branch `codex/guia-atualizado-personalizacao`. Usa a investigação registrada em [INVESTIGATION.md](INVESTIGATION.md) e a conversa “Aplicar REA ao frontend BB Seguros”. A investigação recuperou o catálogo público e a jornada visual, mas não revelou regras privadas de preço, aceitação ou emissão.

## Fontes e divergências

- Guia dos Times, item 10, páginas 13–15: matriz do desafio, restrições, limite básico, personalização e vigência.
- [Página oficial do produto](https://www.bbseguros.com.br/seguros/seguro-empresarial): snapshot público preservado em `plans.json` e evidências REA.
- [Campanha oficial](https://campanhas.bbseguros.com.br/seguro-empresarial/), consultada em 28/10/2026: planos customizáveis, extras conforme atividade e pacotes de assistência.

O guia descreve seis comuns e matrizes 6/8/10. O CSV original e a campanha usam 5/7/9, enquanto o snapshot da página principal associa cibernética e extras. O guia restringe quatro extras de atividade a Prático/Total; a campanha diz qualquer plano conforme atividade. A simulação adota explicitamente o guia, sem alterar os arquivos recebidos ou afirmar que essa matriz seja uma oferta comercial vigente. `product-rules.json` registra a edição e a divergência. Na contratação, as condições oficiais aplicáveis precisam ser conciliadas.

## O que funciona

1. Selecionar empresa/unidade gera imediatamente indicação inicial, com as quatro contas, dez necessidades, patrimônio, fontes, confiança e comparação. Não presume as oito respostas.
2. O formulário confirma relação e situação do imóvel, paredes, foco de proteção, vigência e operações de refrigeração, delivery, bens em trabalho remoto e numerário. Campos desconhecidos não viram “Não”.
3. O motor mantém quatro índices. Acrescenta cibernética às seis comuns obrigatórias e adapta o catálogo em memória. Índices com prioridade >=70 exigem a cobertura na indicação automática, evitando diluição pela média. O foco do cliente multiplica por 1,5 os pesos do grupo correspondente, com efeito rastreável.
4. Triagem anterior à escolha: obra, condenação e parede combustível observadas bloqueiam prosseguimento; objeto básico acima de R$7,5 milhões encaminha ao Seguro Personalizado Empresarial. Valores ausentes geram pendência. O limite considera prédio/conteúdo/estoque sem somar aluguel, RC e demais limites.
5. A tela compara planos padrão e permite escolher um plano, incluir/excluir as quatro ajustáveis no Prático/Total e marcar indispensáveis. As seis obrigatórias são preservadas no servidor. Coberturas explicitamente indispensáveis precisam estar no pacote escolhido.
6. Adicionais operacionais são sugeridos por sinais ou confirmações; inclusão solicitada exige confirmação de operação e plano compatível com a política. Disponibilidade por atividade e aceitação permanecem pendentes. Outros adicionais do guia podem ser solicitados para avaliação. Não há inclusão automática ou contagem desses itens na aderência das dez necessidades.
7. “Aplicar ajustes e recalcular” atualiza composição, faixas e aderência antes/depois. Continuar recalcula novamente para impedir resumo com ajustes pendentes. Alterações nos dados de risco invalidam a análise. Trocar unidade limpa valores, respostas e preferências da unidade anterior.
8. O resultado apresenta faixas monetárias e justificativas por cobertura. RC e cibernética sem base defensável continuam explicitamente pendentes; folha e faturamento não viram indenização inventada. Assistências permanecem fixas. Shopping só sinaliza possível enquadramento após confirmar os quatro requisitos, sem inventar desconto.
9. O resumo JSON inclui pacote escolhido, ajustes, adicionais condicionais, vigência, regras, índices e dimensionamento. Não inclui contato, endereço detalhado ou pagamento bancário. A exportação em lote inclui cibernética, regras versionadas e auditoria. Casos bloqueados têm encaminhamento no resultado e não geram linhas de oferta no template de coberturas.

## API

`POST /api/recomendacao` aceita o contrato anterior e os campos opcionais abaixo. O cliente deve enviar números para vigência e booleanos/nulos para operações.

```json
{
  "priority": "continuidade",
  "termYears": 3,
  "propertyRelation": "tenant",
  "propertyStatus": "REGULAR",
  "wallMaterial": "ALVENARIA",
  "operations": {"refrigeration": true, "delivery": null},
  "indispensable": ["QUEBRA_DE_VIDROS"],
  "selectedPlan": "PRATICO",
  "coverageAdjustments": {"include": ["QUEBRA_DE_VIDROS"], "exclude": []},
  "optionalCovers": ["DETERIORACAO_MERCADORIAS_FRIGORIFICADAS"]
}
```

As propriedades acima complementam atividade/subatividade reais, município/UF, escopo e oito respostas obrigatórias. `selectedPlan` ausente usa a indicação automática. A resposta acrescenta `personalizacao`, contendo triagem, pacote, fontes das regras, confirmações e sugestões. `recomendacao.plano_recomendado` é a referência técnica automática; `personalizacao.pacote.plano` é a escolha efetivamente composta. Em triagem bloqueada, `indicacao_bloqueada=true` prevalece sobre a referência técnica e impede o avanço na página. O JSON não constitui proposta aceita.

## Execução e validação

```powershell
# Na raiz, preparar o Python conforme README.md; os CSVs são locais e não publicados.
cd frontend
npm.cmd run dev
# http://localhost:4174/cotacao
```

Verificação: suíte Python, testes Node, sintaxe JavaScript, HTTP real com os CSVs locais e navegação no navegador. [Evidência agregada do lote](evidence/guia-lote.json) registra 2.978 estabelecimentos e 22.670 linhas de cobertura. Os 78 encaminhamentos por obra não geram oferta; todos os demais pacotes contêm as seis obrigatórias. Evidências públicas não incluem inventários, arquivos originais de clientes ou documentos pessoais.

## Limites que permanecem

Não há tarifa personalizada, emissão, consulta bancária de produção, autorização comercial de API, validação completa de aceitação por atividade, nem tabela contratual de limites/franquias. As estimativas e cortes são hipóteses do MVP. A exportação em lote usa os dados/configurações do motor; as escolhas individuais feitas na página ficam no resumo JSON da simulação e não reescrevem o cadastro ou a configuração global. Os códigos internos da seguradora não são CNAEs. A busca local conecta descrições a itens reais, sem precisar de API generativa. Endereços perturbados não são usados para localizar delegacias.

Evidência visual da conclusão com pacote personalizado: [captura do navegador](screenshots/guia-pacote-personalizado.png). Validação local final: 147 testes Python e 27 testes Node; fluxo HTTP e navegador até a conclusão demonstrativa, sem erros de console.


## Relatório em tela inteira e origem dos dados (formulário .2)

Quando existe resultado cadastral na etapa de empresa, ou nas etapas de planos/revisão/conclusão, a imagem lateral é ocultada e o relatório ocupa a largura disponível (até 1.500 px internos). Ao voltar para preenchimento sem resultado, a jornada de cadastro recupera seu layout. Tabelas têm rolagem interna em telas menores.

A coluna “Origem e confirmação” apresenta os valores usados, arquivo, campos originais e chave empresa/unidade. Agregados de bens explicitam soma de valor × probabilidade, com equipamentos como subconjunto. Um detalhamento separado mostra os bens individuais da unidade e seus valores ponderados. Dados substituídos no formulário ou excluídos pelo escopo não são somados novamente ao inventário original. Documentos pessoais e endereço detalhado não entram nesse relatório.

Cada índice traz leitura contextual com valores da unidade, referência pública com números, período, abrangência e vínculo municipal/CNAE, dados locais e respostas não presumidas, além da memória técnica de fatores, pesos, impacto e vulnerabilidade. A referência de segurança identifica IBGE/SIDRA ou SSP conforme a fonte efetivamente carregada; a de clima expõe frequências e dias válidos da série histórica; NR-4 identifica documento, classe e grau. Vidros informa que não existe API específica integrada. A tela distingue referências armazenadas de consultas ao vivo e conserva ausências em vez de criar dados.

`rastreabilidade.py` acrescenta evidências ao adaptador HTTP, mantendo os índices e regras de recomendação. `BaseDados.bens` conserva somente em memória os registros já carregados para a consulta local por unidade. O resumo JSON inclui a rastreabilidade; os CSVs originais não são alterados. As verificações de rastreabilidade usam fixtures sintéticas e não publicam registros financeiros do cadastro real. Validação desta atualização: 153 testes Python e 29 Node, mais HTTP real e inspeção do navegador.
