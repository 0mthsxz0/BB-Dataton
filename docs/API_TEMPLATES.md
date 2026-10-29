# API de recomendação para os templates

A unidade de consulta é empresa + estabelecimento. Uma empresa com duas unidades gera duas chamadas. A API recebe identificadores, busca os sinais na base carregada e chama `exportacao.analisar_base`, que utiliza o motor, elegibilidade, recomendador e personalização existentes. Não há um segundo algoritmo nem treinamento na base de teste.

O servidor carrega a base inteira antes das consultas. Assim, uma consulta isolada conserva a quantidade real de unidades e os agregados previamente preparados. As oito respostas do formulário não são inventadas para conseguir processar um caso cadastral.

## Fluxo executado

1. Ler cada linha de `template_resultado_times.csv`.
2. Fazer um POST por empresa-estabelecimento.
3. Acrescentar `resultado` ao consolidado.
4. Acrescentar cada item de `coberturas` ao detalhamento.
5. Validar chaves, colunas, coberturas e faixas. Publicar a pasta final somente após todos os casos.

Caso bloqueado retorna HTTP 200 com elegível NAO, motivo e nenhuma linha de cobertura. HTTP 404 indica chave inexistente, não inelegibilidade. Informação insuficiente conserva PENDENTE e confirmações necessárias.

## Executar o preenchimento automaticamente

Na raiz do projeto, no PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/preencher_templates_api.py --dados data/teste --template data/teste/template_resultado_times.csv --saida entregas/templates-teste-api-nova --data-analise 2026-10-29 --comparar-lote
```

Este comando inicia uma API HTTP temporária em uma porta livre de 127.0.0.1, cria um token só em memória, faz uma chamada por linha e encerra o servidor ao terminar. A API responde aos casos antes da comparação em lote. A comparação é uma verificação independente e não fornece as linhas usadas nos CSVs da API. Escolha uma pasta de saída nova a cada execução.

## Manter a API disponível para outras ferramentas

```powershell
$env:BB_TEMPLATES_API_TOKEN = [guid]::NewGuid().ToString('N')
.\.venv\Scripts\python.exe scripts/api_templates.py --dados data/teste --porta 4180 --data-analise 2026-10-29
```

O token permanece na variável do terminal e deve ser enviado pelo cliente em `Authorization: Bearer <token>`. O servidor escuta somente em 127.0.0.1 e rejeita chamadas de páginas de navegador. Não está publicado na internet e não altera o servidor do formulário na porta 4174. Para trocar a base, data ou configuração, reinicie o serviço com os argumentos desejados. `--config` e `--referencias` são opcionais.

### Contrato da consulta

`POST http://127.0.0.1:4180/api/templates/recomendacao`

Cabeçalhos: `Content-Type: application/json` e `Authorization: Bearer <token>`.

```json
{
  "empresa_id": "CASO_00001",
  "imovel_id": "IMO_CASO_00001_01"
}
```

A resposta tem quatro propriedades:

| Propriedade | Conteúdo |
| --- | --- |
| resultado | Objeto com as 12 colunas oficiais do consolidado. |
| coberturas | Lista de objetos com as 11 colunas oficiais do detalhamento. |
| auditoria | Pontuações, dimensionamento, recomendação e personalização desse caso. |
| metadados | Versões, data, configuração, colunas e hashes da base carregada. |

Faixas sem base defensável são JSON null e viram células vazias no CSV, conservando a justificativa. Não usar zero para substituir ausência. Assistências não entram no detalhamento.

`GET /health` verifica disponibilidade sem revelar registros. `GET /api/templates/contrato` exige token e informa o contrato e a base utilizada. Erros: 401 para token inválido, 403 para origem de navegador, 404 para rota/chave inexistente, 415 para formato diferente de JSON, 413 para tamanho inválido, 422 para payload inválido e 500 para falha interna do motor.

O endpoint aceita somente os dois identificadores. Não é uma API pública de cotação e não aceita cadastro arbitrário nem respostas de questionário. Para usar dados de outro conjunto, carregue a base correspondente no servidor. O serviço local é separado das sessões de acesso do portal.

### Cliente apontando para a API já iniciada

```powershell
.\.venv\Scripts\python.exe scripts/preencher_templates_api.py --url http://127.0.0.1:4180 --template data/teste/template_resultado_times.csv --saida entregas/templates-teste-api-servidor
```

O cliente precisa receber o mesmo token na variável `BB_TEMPLATES_API_TOKEN` de seu terminal. Não coloque tokens em arquivos versionados. Em modo `--url`, base, regras e data são definidas exclusivamente pelo servidor.

## Resultado verificado em 29/10/2026

Origem: Seguro_Empresarial_Teste_Comum.zip contido em 1.DADOS.zip.

- 120 empresas e 144 estabelecimentos.
- 144 POSTs de recomendação com HTTP 200, além da consulta inicial ao contrato.
- 1.102 linhas de cobertura.
- Os dois CSVs idênticos byte a byte aos gerados pelo lote, com a mesma base, configuração e data.
- 30 testes aprovados nas suítes de API de templates, exportação de dados e produto.

Os resultados estão em `entregas/templates-teste-api/`. `chamadas_api.json` registra cada consulta, duração, status e hash da resposta. `manifesto_api.json` registra entradas, saídas e equivalência com o lote. `auditoria.json` conserva o raciocínio do motor. Os dois CSVs também foram copiados para `data/teste/`; os templates vazios originais estão preservados em `tmp/templates-teste-originais/`.

Continuam válidas as limitações do motor: elegibilidade preliminar, faixas ausentes justificadas, estimativas sem confirmação humana e ausência de tarifas/emissão. Equivalência com o lote confirma integração e consistência, não qualidade preditiva ou aceitação contratual.

O cliente faz chamadas sequenciais e para ao primeiro erro. Não publica uma entrega parcial e não sobrescreve pastas anteriores. Esta versão não possui retomada automática, paralelismo nem infraestrutura de produção.
