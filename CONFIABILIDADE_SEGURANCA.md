# Confiabilidade da referência de segurança

Verificação em 28/10/2026. O sistema não possui um índice de criminalidade empresarial calibrado. O que oferece é uma prioridade heurística de proteção, com origem dos dados e exclusões auditáveis. Fonte oficial, arquivo local e hash são condições de rastreabilidade; não eliminam subnotificação, revisões, diferenças de classificação ou erro do modelo.

## O que foi conferido no Sinesp

Na [página oficial VDE](https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/dados-nacionais-1/base-de-dados-e-notas-metodologicas-dos-gestores-estaduais-sinesp-vde-2022-e-2023), existem planilhas anuais de 2015 a 2026. Foi baixado o [arquivo de 2025](https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica/download/dnsp-base-de-dados/bancovde-2025.xlsx/@@download/file), último ano civil encerrado na data desta análise. Sua cópia integral está em `data/referencias/cache/sinesp/bancovde-2025.xlsx`; as notas metodológicas estão em `notas_metodologicas.html` na mesma pasta.

A inspeção encontrou 832.302 linhas, 31 categorias e meses de janeiro a dezembro. A planilha tem município e UF, sem coluna de código IBGE. Possui abrangências Estadual, Polícia Federal e Polícia Rodoviária Federal; não se deve somá-las indiscriminadamente. A presença dos doze meses no arquivo não garante completude por município/categoria.

Não foi encontrada categoria de roubo em comércio. Roubo de veículo, de carga e a instituição financeira não são equivalentes. Por isso, esse arquivo **não alimenta a avaliação de roubo empresarial**. Não foi produzido um indicador substituto com homicídios nem uma taxa por população apresentada como risco de estabelecimento.

[references/auditoria_sinesp_2025.json](references/auditoria_sinesp_2025.json) registra URL, data real do download, SHA-256 dos originais e das notas, colunas, categorias e resultado. A análise foi feita com o leitor local `scripts/auditar_sinesp.py`, que não acessa a rede. O arquivo de 2026 não foi usado porque ainda corresponde a ano em curso.

Para repetir a inspeção, preserve o original e a data real do download:

```powershell
.\.venv\Scripts\python.exe scripts/auditar_sinesp.py --arquivo data/referencias/cache/sinesp/bancovde-2025.xlsx --fonte "URL_OFICIAL_DO_DOWNLOAD" --baixado-em "DATA_ISO_COM_FUSO" --notas data/referencias/cache/sinesp/notas_metodologicas.html --saida data/auditoria_sinesp_reproducao.json
```

O arquivo integral fica localmente em `data/`, que é ignorado pelo Git. Para reproduzir em outra máquina é necessário transferir esse original ou obtê-lo e conferir o hash registrado; o servidor pode revisar a planilha publicada sob a mesma URL.

## Regra aplicada ao índice

A política `seguranca-1.0` exclui a antiga proxy domiciliar IBGE/PNAD 2021. O snapshot continua disponível para consulta histórica, sem contribuir para a pontuação empresarial. Uma referência SSP de roubo em comércio somente pode contribuir quando cumpre todas as condições:

- Código municipal de sete dígitos compatível com a UF e categoria `ROUBO_EM_COMERCIO`.
- Ano civil encerrado, doze meses observados e cobertura municipal completa declarada sem sobreposição.
- Contagens inteiras não negativas; estabelecimentos inteiros positivos, do mesmo ano, com fonte documentada. População não substitui estabelecimentos nesse indicador.
- Taxa e transformação coerentes com as contagens e o denominador. Zero observado é distinto de ausência.
- SHA-256 do snapshot compatível com o manifesto previamente gravado e hashes dos arquivos originais presentes. Manifesto ausente impede o uso; divergência de hash interrompe o carregamento.
- Validade editorial de até 24 meses após dezembro do ano observado. Esse limite é uma regra do projeto, não uma garantia estatística.

O importador SSP exige `fonte_denominador` e `ano_denominador` no manifesto. Sem eles, conserva a contagem, mas não gera taxa utilizável. Importações antigas precisam ser refeitas. Ele grava `seguranca_ssp.csv.manifesto.json`, mantém versões dos downloads por hash e registra os novos downloads com data. Hash não é assinatura nem prova de autenticidade se arquivo e manifesto forem alterados juntos.

Referência elegível recebe status **EXPERIMENTAL**, pois a transformação e os pesos não foram calibrados por sinistros. Nenhum status significa “100% confiável”. A seleção e abrangência do denominador e a equivalência das definições ainda exigem conferência substantiva da equipe.

Referência ausente, incompatível ou vencida usa componente territorial neutro de 0,5 com confiança zero e sensibilidade ampliada. Esse 0,5 é uma convenção para lidar com desconhecimento, sem taxa observada. A prioridade de proteção pode continuar a partir do patrimônio e das declarações, acompanhada do motivo da exclusão. A confiança do modelo não é precisão estatística.

## Auditoria e atualização

Tela, resposta do formulário e auditoria em lote expõem status, motivo, data da análise e versão da política. A troca de cidade remove metadados e simulações anteriores. A consulta opcional de localização por CEP/município continua podendo acessar ViaCEP/IBGE; o cálculo e a validação das referências não acessam a rede.

A exportação registra `data_analise`. Para reproduzir a decisão de validade, use os mesmos arquivos, versão do código, configuração e data:

```powershell
.\.venv\Scripts\python.exe cli.py --dados "PASTA_DOS_CSVS" --data-analise 2026-10-28 --saida output/reproducao
```

Revisar trimestralmente fontes, cobertura e notas metodológicas; baixar uma nova versão deliberadamente e conservar a anterior. Antes de apresentar o índice como validado, será necessário obter referência comercial compatível, validar o denominador e testar a calibração com dados de sinistros e avaliação especializada. Os testes de software verificam a aplicação das regras, sem comprovar a qualidade estatística da previsão.
