# Banco público de segurança e contrato do motor principal

## Estado verificado em 29/10/2026

A preparação do software está implementada na branch dados-de-seguranca. O contrato foi conferido contra a main no commit b8c86080d97ebd493c503a02fac5b6130c741fff.

**A cobertura real do indicador exigido pelo motor ainda está pendente.** Não há CSV de produção elegível para exportar. Isso é diferente de afirmar que o banco está vazio ou que a integração está concluída.

| Item | Resultado |
| --- | --- |
| Arquivo SINESP VDE 2025 | Baixado diretamente do MJ, 26.644.100 bytes |
| SHA-256 do original | 6b87609815afc534f44f3423bf8660a69c961130c187f759b9d3e38ee2a8a6e8 |
| Recorte de roubo no SQLite | 69.510 registros, com unidade, abrangência e origem preservadas |
| Cadastro/denominadores IBGE neste ambiente | Pendente: API retornou HTTP 503 |
| ISP-RJ e SSP-RS nesta tentativa | Pendentes: conexão recusada pelo proxy com HTTP 403 |
| Referência comercial elegível para a main | Nenhuma |
| Integridade SQLite / violações FK | ok / zero |
| Empresas, bens ou estabelecimentos do Datathon | Não importados nesse banco |

O download direto do SINESP funcionou, embora a navegação do portal tivesse falhado anteriormente. Isso não comprova que todos os arquivos do site foram baixados.

O arquivo inteiro contém 832.302 linhas de diversas categorias. O original foi preservado; a tabela vde_registros contém o recorte de roubo, não todas as categorias do arquivo.

## O que o motor principal aceita

A main exige roubo em comércio municipal, contagem de ocorrências, ano civil encerrado, doze meses completos, denominador de estabelecimentos do mesmo ano, URLs/fontes, hashes e uma transformação territorial coerente.

Ela não aceita substituir essa referência por:
- Taxa domiciliar PNAD.
- Taxa por população.
- Roubo de veículo, carga ou instituição financeira.
- Contagem de vítimas.
- Total estadual distribuído entre municípios.
- Índice Mosler.

A referência deve satisfazer a política seguranca-1.0; parâmetros válidos não significam calibração por sinistros.

## Componentes entregues

- seguranca/motor_principal.py: importação de referência pública revisada, consulta somente de dados elegíveis e exportação para o contrato da main.
- seguranca/politica_motor.py: política do motor principal identificada pelo commit de origem.
- Compatibilidade dos imports do pacote seguranca com as funções, constante e prefixos usados pela main. Não é necessário sobrepor os arquivos do motor ao banco.
- scripts/preparar_banco_seguranca.py: preparação repetível de fontes, importação pública, diagnóstico e verificação de integridade.
- Importação VDE --somente-bruto: preserva os registros antes de haver cadastro municipal, sem publicar ocorrências municipais.
- Auditoria de cobertura em leitura: pode associar um arquivo do consumidor em memória, mas não grava empresas/estabelecimentos no banco de segurança.

O banco e os arquivos brutos permanecem em data/seguranca, ignorados pelo Git. Um clone do código não contém automaticamente esses arquivos.

## Preparação

Na raiz desta branch, com as dependências instaladas:

```bash
python scripts/preparar_banco_seguranca.py --saida data/seguranca/pacote-main-NOVA-EXECUCAO
```

O script tenta as fontes oficiais e aproveita downloads cujo hash/URL foram verificados. Para usar somente o cache:

```bash
python scripts/preparar_banco_seguranca.py --sem-rede --saida data/seguranca/pacote-main-OFFLINE
```

Cada execução precisa de uma pasta de saída nova. Código de saída 2 e PENDENTE_FONTES_COMPATIVEIS significam preparação parcial. Diagnósticos são gravados; não se publica um CSV vazio como base pronta.

Fontes estaduais continuam usando os adaptadores revisados existentes da branch; não são convertidas em referência empresarial sem o denominador correto e a revisão do contrato.

## Entrada de uma referência pública revisada

Os importadores de fontes e o produtor da referência precisam fornecer o snapshot compatível com o motor. A main já possui scripts/importar_ssp.py para preparar fontes configuradas por manifesto; o número de estabelecimentos e sua fonte precisam ser conhecidos, do mesmo ano dos eventos.

A referência normalizada deve ter as colunas definidas em COLUNAS de seguranca/motor_principal.py e um arquivo adjacente NOME.csv.manifesto.json com mapa arquivos: {NOME.csv: SHA256}. A importação recusa arquivos com identificadores de clientes, simulação, categorias incompatíveis, taxas inconsistentes e hashes divergentes.

```bash
python -m seguranca importar-referencia-motor /caminho/referencia_publica.csv
python -m seguranca consultar-motor --codigo 3304557
python -m seguranca exportar-motor --saida data/seguranca/pacote-main-VALIDADO
```

Hash confere integridade do snapshot, não autentica sozinho o conteúdo da fonte. Fontes originais e denominador devem ser revisados antes de congelar o manifesto.

A cada consulta/exportação a validade temporal é reavaliada. Referência vencida não continua utilizável por ter sido importada no passado. Referências divergentes do mesmo município/ano exigem revisão; não são substituídas silenciosamente.

## Uso pelo motor da main

Quando houver referência elegível, a exportação produz:
- seguranca_ssp.csv;
- seguranca_ssp.csv.manifesto.json;
- diagnostico_motor.json.

Copie o CSV e o manifesto juntos para data/referencias da aplicação principal. O carregador da main já reconhece seguranca_ssp.csv e preserva as demais referências distribuídas de clima/NR-4. Alternativamente selecione a pasta completa na configuração de referências.

O pacote CSV evita acoplar o motor diretamente ao schema SQLite e permite manter as duas branches separadas. Não se deve fazer um merge integral das interfaces para consumir a base.

Neste ambiente, não foi produzido esse CSV de produção, pois ainda não há linhas elegíveis. O teste ponta a ponta que demonstrou aceitação pela main usou fixture sintética isolada e não foi inserido no banco real.

## Consultas ao banco real

```sql
SELECT uf, crime, mes, abrangencia, metrica, valor, status
FROM vde_registros
ORDER BY uf, crime, mes;

SELECT metrica, COUNT(*) AS registros
FROM vde_registros
GROUP BY metrica;
```

A tabela contém 67.566 linhas de vítimas, 967 de ocorrências e 977 com valor ausente, incluindo diferentes abrangências. Esses números são quantidades de linhas, não totais de crimes. As linhas de ocorrências disponíveis no arquivo não fornecem a série de roubo em comércio municipal necessária ao motor.

Após atualizar o IBGE, uma importação municipal explícita pode revisar a correspondência. Ela não deve reaproveitar o status da coleta bruta como autorização de uso.

## Verificações e próximos dados necessários

A suíte da branch verifica importação, incompatibilidades, hashes, validade, exportação, integridade e ausência de persistência de clientes. O pacote de teste foi carregado por incorporar_ssp e aceito por avaliar_seguranca do código da main. Os testes de segurança/localização da main também foram executados com o pacote Python presente para verificar a compatibilidade dos nomes.

Para liberar cobertura real, ainda é necessário obter:
1. Cadastro e indicadores oficiais IBGE acessíveis.
2. Séries municipais completas de roubo em comércio.
3. Denominador oficial compatível de estabelecimentos do mesmo ano.
4. Revisão das definições e congelamento dos arquivos/manifestos.

Uma fonte de 2024 pode ser usada se atender à validade do motor e tiver denominador 2024; não é necessário fingir que uma série 2025 incompatível atende ao contrato.

Os diagnósticos desta preparação estão em [verificacao.json](evidencias-motor-main/verificacao.json), [coleta.json](evidencias-motor-main/coleta.json) e [preparacao.json](evidencias-motor-main/preparacao.json). Os relatórios históricos de coleta em outro ambiente permanecem históricos; não foram usados para inventar registros ausentes aqui.

