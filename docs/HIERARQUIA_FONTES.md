# Hierarquia de fontes de segurança

**Registro da abordagem anterior.** Para o novo cruzamento IBGE + SINESP + CSV
por estabelecimento, consulte o [relatório Mosler](RELATORIO_INDICE_SEGURANCA_MOSLER.md).
O comando `avaliar-mosler` não aciona esta ordem de fornecedores nem usa SSPs
como substitutas automáticas do SINESP. A implementação abaixo permanece como
histórico reproduzível e permite consultar indicadores estaduais separadamente.

Implementada na branch `dados-de-seguranca`, com execução real para janeiro a
dezembro de 2025. A configuração é [config/fontes_seguranca.json](../config/fontes_seguranca.json).
O cadastro e os denominadores continuam vindo do IBGE; a hierarquia abaixo resolve
as séries de ocorrências municipais.

## Ordem e condições

| Prioridade | Classe | Requisitos |
| --- | --- | --- |
| 1 | Órgão oficial produtor — SSP, instituto estadual ou polícia responsável | Arquivo municipal, unidade de contagem documentada, definição revisada, dados consolidados |
| 2 | Consolidação oficial — por exemplo SINESP | Os mesmos requisitos de compatibilidade; ser federal não torna um total estadual municipal |
| 3 | Republicação verificada | Revisão metodológica e hash idêntico ao original oficial previamente conferido; nenhuma ativada nesta edição |

A ordem é uma política de preferência justificada pela proximidade da produção
e pela documentação, não um percentual estimado de confiabilidade. Uma fonte de
nível 1 que publica vítimas ou dados estaduais é recusada para a consulta de
ocorrências municipais, e o motor continua para o nível seguinte.

A seleção é por **município + indicador + janela de doze meses**. Se a primeira
fonte não tem todos os meses válidos, a próxima precisa fornecer a série completa.
Não se montam onze meses de uma definição com um mês de outra. Zero explícito é
dado; vazio não é zero. Divergências entre fontes completas ficam registradas,
sem somar suas contagens. O mesmo arquivo com chaves duplicadas é recusado.

Os requisitos incluem código IBGE válido, município, unidade de ocorrências,
definição aceita para o indicador, consolidação e mês encerrado. Mudança de
definição dentro da série também impede seleção. HTTP/TLS, download ou layout
inválido são falhas daquela fonte: ficam no diagnóstico e não interrompem a
tentativa da próxima. Não se desliga a validação TLS.

Quando todas as **fontes cadastradas e revisadas** se esgotam, fica uma lacuna com
os motivos de cada tentativa. O sistema não afirma que esgotou toda a internet ou
que um dado não existe. A seleção automática não dispensa desenvolver e validar
adaptadores para novos publicadores/layouts.

## Integrações reais desta edição

| Fonte | Arquivo inspecionado | Seleção efetiva |
| --- | --- | --- |
| ISP-RJ | CSV municipal e dicionário XLSX | 92 municípios, quatro indicadores completos: veículo, carga, comércio e banco |
| SSP-RS | XLSX 2025, abas JAN–DEZ e totais estaduais | 494 municípios com nome/UF correspondentes ao IBGE, veículo e latrocínio em ocorrências |
| SINESP VDE 2025 | XLSX integral já auditado | Nenhuma série de ocorrências municipais compatível; vítimas e agregados sem município não foram convertidos |

No RS, o adaptador distingue `Latrocínio` de `Vítimas de Latrocínio`, confere o ano,
497 linhas municipais por aba e reconcilia as contagens com os totais publicados.
Três grafias sem correspondência exata permanecem na auditoria da fonte. A
formatação residual até a coluna XFD não é interpretada como dados.

No RJ, o dicionário confirma contagem em **casos** para veículo, carga, comércio
e banco; a coluna `latrocinio` conta **vítimas** e fica excluída. A fase precisa
ser consolidada (2 ou 3). Roubo a banco permanece separado de roubo a instituição
financeira. O método do ISP para carga não é automaticamente equivalente ao
agrupamento enviado ao SINESP.

## Resultado observado

- 33.426 séries solicitadas: 5.571 localidades × seis indicadores.
- **1.356 séries completas selecionadas**, equivalentes a **16.272 observações mensais**.
- 988 séries da SSP-RS e 368 do ISP-RJ, com hash e definição por registro.
- **527 de 2.978 estabelecimentos** com algum indicador completo (RJ e RS).
- **302 estabelecimentos** com roubo em comércio observado (RJ).
- 32.070 séries ainda sem fonte compatível no catálogo desta edição.
- O índice combinado original continua indisponível, com pesos CRITIC vazios.

Esses números são cobertura parcial de indicadores, não cobertura de um índice
nacional validado. O cálculo exige todos os critérios da configuração; a ausência
de instituição financeira não é preenchida com banco. Se uma futura coorte reunir
definições diferentes para o mesmo critério, o cálculo bloqueia o ranking conjunto
até existir equivalência documentada. A hierarquia não recalibra pesos nem altera
a seleção de crimes para conseguir um ranking.

Exemplo conferido na fonte e na API: Rio de Janeiro, 2025, tem 1.113 registros de
roubo em comércio, 13.713 de veículo, 1.496 de carga e zero de roubo a banco. Porto
Alegre tem 628 roubos de veículo e três ocorrências de latrocínio no recorte da
SSP-RS. Não interpretar essas contagens como probabilidade individual de sinistro.

O formulário mostra os indicadores disponíveis, o período e o link da fonte,
mesmo quando não pode apresentar o índice combinado. Não recomenda plano nem
pontua patrimônio com esses dados sem validação empresarial.

Evidências: [diagnóstico da execução](evidencias-seguranca/hierarquia.json),
[cobertura agregada dos estabelecimentos](evidencias-seguranca/cobertura-hierarquia.json),
[consultas HTTP reais](evidencias-seguranca/api-hierarquia.json) e
[consulta no navegador](evidencias-seguranca/formulario-hierarquia-rio.png).

## Execução e saídas

```powershell
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe -m seguranca resolver-fontes --fim 2025-12
.\.venv\Scripts\python.exe -m seguranca gerar-indice --fim 2025-12
.\.venv\Scripts\python.exe -m seguranca auditar --estabelecimentos ../Seguro_Empresarial_Desenvolvimento/enderecos_estabelecimentos.csv --saida data/seguranca/auditoria/desenvolvimento
```

`resolver-fontes` retorna 2 se existem lacunas; os dados válidos e o diagnóstico
são preservados. `--atualizar` solicita nova coleta; sem ele, o cache é conferido
por URL e SHA-256. A edição atual exige ano civil encerrado (`AAAA-12`); as URLs
da SSP-RS e do VDE referem-se a 2025. Outra edição exige atualizar a política e
revisar as publicações. O VDE precisa de `importar-vde` antes da resolução.

Em `data/seguranca/hierarquia/`:

- `diagnostico_hierarquia.json`: resultado, fontes/hashes e falhas de coleta/validação.
- `decisoes_fontes.jsonl`: seleção ou lacuna e tentativas por município/indicador.
- `series_municipais_selecionadas.csv`: observações efetivamente utilizadas, com código IBGE, definição, fornecedor, URL e hash.
- `manifesto_hierarquia.json`: política, snapshots e hashes dessas três saídas.

O SQLite conserva candidatos separados das ocorrências selecionadas. A publicação
troca somente vínculos geridos pela hierarquia; um conflito com fonte legada
reverte a transação. Reexecutar não duplica as séries. Atualizar fontes invalida
os índices, que precisam ser regenerados. Não há download durante a consulta do
formulário; a coleta é um comando de preparação.

Para um novo adaptador revisado, há também o contrato `csv_normalizado`, com
`codigo_ibge,crime,mes,valor,metrica,granularidade,definicao,consolidado`. Consolidação
exige `SIM/NAO`. Não basta renomear uma coluna de vítimas para ocorrências ou declarar
uma definição aprovada sem verificar o dicionário e a origem.

## Fontes adicionais encontradas e limites atuais

Foram localizados portais oficiais de SP, MG, PR, BA, CE, GO e PE. Eles ainda não
foram ativados como adaptadores municipais nesta política: alguns usam painéis,
PDFs ou outros layouts, e a unidade/definição precisa ser conferida por arquivo.
O endpoint de catálogo MG retornou 403 e a página de dados abertos 503 na coleta
local; a abertura do portal PE falhou com 500 pela ferramenta web. Isso não prova
inexistência de dados. O registro de DF continua pendente de fonte e revisão
territorial explícitas; não se somaram regiões administrativas.

Referências para revisão: [SP](https://www.ssp.sp.gov.br/estatistica/dados-mensais),
[MG](https://dados.mg.gov.br/dataset/dados-abertos-ocorrencias-policiais),
[PR](https://www.seguranca.pr.gov.br/CAPE/Estatisticas),
[BA](https://www.ba.gov.br/ssp/estatistica),
[CE](https://www.ce.gov.br/sspds/html/estatisticas-2025/),
[GO](https://goias.gov.br/seguranca/estatisticas/),
[PE](https://www.sds.pe.gov.br/estatisticas).

Validação realizada: **127 testes Python**, **23 testes do frontend**, checagem
sintática JavaScript, conferência de hashes/CSV e dez consultas HTTP reais.
Os testes incluem fonte indisponível, primeira fonte incompleta, unidade errada,
zeros, mudanças de definição, revisão de snapshot, conflito com legado e bloqueio
de ranking entre definições não equivalentes.
