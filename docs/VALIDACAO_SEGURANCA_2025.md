# Validação real da base de segurança — 28/10/2026

A coleta foi concluída e a base local foi alimentada. O índice municipal original
**não é calculável com o VDE 2025 inspecionado**. Não se trata mais de bloqueio de
download: faltam a granularidade e a unidade exigidas pelo método. CRITIC e ranking
ficam indisponíveis, sem substituição por pesos manuais, vítimas ou dados estaduais.

## Entradas confirmadas

| Entrada | Resultado |
| --- | --- |
| Cadastro IBGE atual | 5.571 localidades, código de sete dígitos e UF |
| População IBGE | Estimativa 2025, agregado 6579, variável 9324; 5.571 correspondências exatas de código |
| Área IBGE | Censo 2022, agregado 4714, variável 6318; não é área territorial de 2025 |
| Área ausente no Censo 2022 | Boa Esperança do Norte/MT, 5101837; permanece vazia |
| VDE 2025 | 832.302 linhas, 14 colunas, 31 categorias, janeiro a dezembro |
| Recorte de roubos preservado | 69.510 linhas em `vde_registros` |
| Estabelecimentos do desenvolvimento | 2.978, dez municípios/UFs, nenhuma chave empresa–unidade duplicada |

O GET oficial do VDE concluiu 26.644.100 bytes, com SHA-256
`6b87609815afc534f44f3423bf8660a69c961130c187f759b9d3e38ee2a8a6e8`.
Coincide com a cópia da auditoria anterior. Os JSONs do IBGE também têm hashes e
horários de coleta. [Snapshot auditável](evidencias-seguranca/snapshot.json).

O portal do MJ pode retornar 403 e `requests` apresentou falha TLS nesta máquina;
o download do arquivo com `curl.exe -L --fail` funcionou com validação TLS ativa.
Isso confirma acesso aos arquivos utilizados, sem afirmar liberação irrestrita
de todo o portal ou reconexão do antigo ambiente remoto.

## O que as colunas reais permitem

| Evento | Unidade no arquivo | Localização | Consequência |
| --- | --- | --- | --- |
| Roubo de veículo | `total` | `NÃO INFORMADO` | Não há ocorrência municipal |
| Roubo de carga | `total` | `NÃO INFORMADO` | Não há ocorrência municipal |
| Roubo a instituição financeira | `total` | `NÃO INFORMADO` | Não há ocorrência municipal |
| Roubo seguido de morte (latrocínio) | `total_vitima`; `total` vazio | Municípios, com problemas de correspondência e repetição | Vítimas não substituem ocorrências |

Nos três primeiros eventos, cada abrangência (Estadual e Polícia Federal) tem
324 linhas por evento, 27 UFs × 12 meses. A palavra `Estadual` identifica a
abrangência de registro; não comprova localização municipal. Não se atribui nem
mesmo o total do DF a Brasília sem documentação de correspondência.

No recorte estadual desses três eventos há cinco valores ausentes (três em
instituição financeira e dois em carga) e 402 zeros explicitamente publicados.
Zeros foram preservados como observações; vazios continuam ausentes. Não se
misturam abrangências nem se distribuem totais estaduais pela população.

A planilha complementar oficial `indicadoressegurancapublicamunic_.xlsx` também
foi baixada e inspecionada: 27 abas e 60.459 linhas, com coluna `Vítimas`, sem
série identificada de ocorrências dos tipos de roubo exigidos. Não resolve a lacuna.

## Auditoria e cobertura

As 69.510 linhas de roubo foram classificadas sem descartá-las do banco:

| Situação principal | Linhas |
| --- | ---: |
| Vítimas, sem unidade de ocorrência compatível | 66.756 |
| Abrangência não estadual | 972 |
| Município não informado | 1.314 |
| Chave municipal repetida (Brasília) | 396 |
| Município sem correspondência exata nome/UF | 72 |

Há 30 chaves estaduais repetidas no recorte bruto, envolvendo 432 linhas: 396 de
Brasília (33 linhas em cada mês) e 36 de município não informado. As categorias da
tabela acima são exclusivas e seguem prioridade; por isso repetições sem município
estão no grupo `Município não informado`. Não houve soma ou deduplicação silenciosa.

As 72 linhas sem correspondência são doze meses de seis grafias: Barão de Monte
Alto/MG, Santo Antônio do Leverger/MT, Arês/RN, Açu/RN, São Luiz/RR e Gracho
Cardoso/SE. Não foram aplicadas correspondências aproximadas ou aliases sem revisão.

O banco passou em `integrity_check` e `foreign_key_check`; nenhuma chave mensal
duplicada entrou em `ocorrencias`. A tabela de ocorrências municipais está vazia,
e não preenchida com zeros artificiais. A grade de lacunas tem 22.284 pares
município/critério; cada um tem os doze meses de 2025 indisponíveis para o contrato
de ocorrências. Isso não significa que não existam dados de vítimas no arquivo.

| UF | Estabelecimentos | Correspondência IBGE | Com índice municipal |
| --- | ---: | ---: | ---: |
| BA | 213 | 213 | 0 |
| CE | 188 | 188 | 0 |
| DF | 425 | 425 | 0 |
| GO | 268 | 268 | 0 |
| MG | 304 | 304 | 0 |
| PE | 207 | 207 | 0 |
| PR | 275 | 275 | 0 |
| RJ | 302 | 302 | 0 |
| RS | 225 | 225 | 0 |
| SP | 571 | 571 | 0 |
| **Total** | **2.978** | **2.978 (100%)** | **0 (0%)** |

Os estabelecimentos são fictícios, conforme o LEIA-ME do pacote do desafio;
códigos, municípios e UFs são referências reais. O pacote e os arquivos por unidade
permanecem locais em pastas ignoradas pelo Git. A evidência versionada é agregada.

## Exportação e formulário

Saídas locais, relativas à raiz desta branch:

- `data/seguranca/seguranca.sqlite`: cadastro, denominadores, registros VDE e identificadores dos estabelecimentos.
- `data/seguranca/exportacao/indice_municipal.csv`: 5.571 linhas, população/ano, área/ano, índice vazio e faixa `indisponivel`.
- `data/seguranca/exportacao/cobertura_uf.csv`: 27 UFs, todas sem índice.
- `data/seguranca/exportacao/diagnostico.json`: `pesos_critic={}` e `topo_revisao=[]`.
- `data/seguranca/exportacao/manifesto.json`: fontes e hashes das exportações.
- `data/seguranca/auditoria/desenvolvimento/`: cobertura por UF, associação das 2.978 unidades e grade de meses ausentes.

A consulta HTTP real foi validada nos dez municípios dos estabelecimentos:
todos retornam 200, município e população corretos, índice `null` e
`uso_empresarial_validado=false`. Busca sem acento, código inexistente e UF inválida
foram conferidos. O navegador identificou São Paulo e exibiu indisponibilidade,
sem tratar falta de dados como risco baixo. [Evidência da consulta](evidencias-seguranca/formulario-sao-paulo.png).

O formulário apresenta **contexto municipal de roubos**, declara a ausência de
roubo em comércio e não gera pontos de necessidade ou indicação de plano a partir
desse contexto. Um valor contextual futuro não se torna probabilidade de roubo
de um estabelecimento. A API e o CSV preservam o campo histórico
`indice_roubo_0_100` por compatibilidade.

## Reprodução

Com o ambiente virtual da branch e as entradas já baixadas:

```powershell
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe -m seguranca importar-ibge --localidades data/seguranca/fontes/ibge/ibge_municipios.json --indicadores data/seguranca/fontes/ibge/ibge_censo_2022.json
.\.venv\Scripts\python.exe -m seguranca importar-populacao data/seguranca/fontes/ibge/ibge_estimativa_2025.json --ano 2025 --url 'https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/2025/variaveis/9324?localidades=N6[all]'
.\.venv\Scripts\python.exe -m seguranca importar-vde data/seguranca/fontes/sinesp/bancovde-2025.xlsx --url 'https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/download/dnsp-base-de-dados/bancovde-2025.xlsx/@@download/file' --auditoria data/seguranca/exportacao/auditoria_vde_2025.json
.\.venv\Scripts\python.exe -m seguranca gerar-indice --fim 2025-12
.\.venv\Scripts\python.exe -m seguranca auditar --estabelecimentos ../Seguro_Empresarial_Desenvolvimento/enderecos_estabelecimentos.csv --saida data/seguranca/auditoria/desenvolvimento
$env:BB_PYTHON = (Resolve-Path .venv/Scripts/python.exe).Path
$env:PORT = '4175'
node frontend/server.mjs
```

O comando de índice retorna **2** quando nenhum índice é calculável; ainda assim
salva as exportações de indisponibilidade. Não interpretar esse código como falha
de conexão. `importar-vde` retorna 0 pela preservação bem-sucedida dos registros,
informando separadamente as zero ocorrências municipais importadas.

Em outro terminal, `python scripts/validar_base_seguranca.py --api http://localhost:4175`
confere o snapshot de 2025 e os resultados da API. Esse script possui controles
explícitos desta edição; não é um validador genérico para outras populações/anos.
Na sessão local foi reutilizado o Python do checkout vizinho `BB-Dataton/.venv`.

Verificações de software: **115 testes Python**, **23 testes do frontend** e
checagem sintática JavaScript passaram. Isso verifica importadores e contratos;
não calibra risco atuarial nem corrige limitações de registro da fonte.

## Pendência para um ranking

É necessária uma fonte municipal de ocorrências com definição e cobertura
compatíveis, ou uma revisão explícita do objetivo para um índice estadual.
Um índice estadual exigiria outros denominadores, coorte de 27 UFs, revisão dos
parâmetros e apresentação da granularidade. Não é uma simples substituição de
código IBGE. Um índice só de vítimas de latrocínio também seria outra medida,
com outra interpretação. Não se publica qualquer uma delas como risco de roubo
de comércio sem evidência e validação externas.
