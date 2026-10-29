# Protege Empresa | BB Datathon

## Modelo de segurança: cruzamento integrado com Mosler

O modelo proposto cruza IBGE, SINESP e CSV em cada estabelecimento, conforme o
[relatório Mosler e justificativa dos pesos](docs/RELATORIO_INDICE_SEGURANCA_MOSLER.md).
Use `python -m seguranca avaliar-mosler --help`. O novo comando preserva a
proveniência SINESP e não aciona a prioridade entre fornecedores da etapa anterior.
Pesos e notas qualitativas são experimentais e exigem evidências documentadas.

### Histórico da coleta e das fontes complementares

A [hierarquia de fontes anterior](docs/HIERARQUIA_FONTES.md) selecionou 16.272
observações mensais completas do RJ/RS, com algum indicador para 527 dos 2.978
estabelecimentos; 302 têm roubo em comércio. Fontes incompatíveis ou incompletas
cedem lugar à próxima, com motivos registrados. O índice combinado ainda tem
critérios sem cobertura e permanece indisponível.

Na auditoria inicial da branch `dados-de-seguranca`, a coleta oficial foi retomada e o banco local
alimentado: 5.571 localidades IBGE, população estimada de 2025, área censitária de
2022 e 69.510 registros de roubo do VDE 2025. Os 2.978 estabelecimentos têm código
IBGE validado. A cobertura do índice municipal é **0%**: no VDE, os três tipos de roubo
com contagem de ocorrências estão sem município; latrocínio mede vítimas.
Pesos CRITIC e ranking ficam indisponíveis, e o formulário declara esse limite.
Veja [a auditoria, as saídas e a reprodução](docs/VALIDACAO_SEGURANCA_2025.md).

## Base de segurança municipal

**Modelo integrado proposto:** o [relatório Mosler](docs/RELATORIO_INDICE_SEGURANCA_MOSLER.md)
explica o cruzamento conjunto IBGE + SINESP + CSV por estabelecimento, os pesos
experimentais e a fórmula. A implementação é executada por `python -m seguranca
avaliar-mosler --help`; requer notas qualitativas documentadas, não presumidas.

A branch `dados-de-seguranca` inclui coleta SINESP/IBGE, banco SQLite consultável,
índice relativo de roubo com suavização e pesos CRITIC, exportação CSV e integração
com o formulário. Consulte [fontes, comandos, método e limitações](docs/DADOS_DE_SEGURANCA.md).
Os dados reais e os limites de granularidade constam da validação acima. Os
arquivos brutos permanecem locais e podem não existir em outra instância do
ambiente. Dados ausentes não recebem índice zero.

## Portal e formulário web

O diretório [frontend/](frontend/) contém a home, o Seguro Empresarial e um formulário demonstrativo de seis etapas, sem campo CPF. A seleção econômica tem as 970 atividades do catálogo público, nomes por extenso e busca por lista, nome ou descrição do negócio, com sugestão de subatividade.

Para abrir: `cd frontend` e `npm run dev` (no PowerShell, `npm.cmd run dev`). Acesse http://localhost:4174/cotacao. Não há dependências npm a instalar. A busca é local; os dados preenchidos não são enviados à seguradora. Pagamento e conclusão são demonstrativos, sem emissão ou cobrança. Consulte [a documentação do formulário](frontend/docs/COTACAO.md) para fontes, testes e limites.

O front-end não altera as regras do motor Python descrito a seguir.

Versão 0.3: combina os quatro índices multifatoriais contínuos (roubo/furto, vendaval, RC empregador e vidros) com cinco heurísticas de preferência das coberturas comuns. O plano considera **nove necessidades**, meta padrão de **80% de aderência** e coberturas das quais o usuário **não abre mão**. Não converte os quatro índices em categorias de 25/55/85 pontos nem os multiplica novamente pelo patrimônio. As nove coberturas continuam dimensionadas e exportadas; não há preços nos arquivos do Datathon.

Aderência = pontos ponderados presentes no plano / pontos ponderados das nove necessidades. Escolhe-se o menor nível que atinge a meta e contém todas as indispensáveis. As preferências da barra lateral valem para todas as unidades da sessão e da exportação; ficam registradas na configuração e auditoria. Aderência mede presença no catálogo, não qualidade contratual, probabilidade ou garantia de indenização. Os cinco valores heurísticos são explicitamente identificados; não são novos modelos físicos de sinistro.

## Executar

Python 3.12 ou 3.13. No PowerShell:

    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    .\.venv\Scripts\python.exe scripts/importar_dados.py "CAMINHO_DOS_CSVS"
    .\.venv\Scripts\python.exe -m streamlit run app.py

No Linux/macOS, use .venv/bin/python. Para reproduzir as versões da validação, instale requirements-lock.txt. A interface abre normalmente em http://localhost:8501.

Os nove CSVs fornecidos pela organização não são publicados no Git. A aplicação reconhece data/desenvolvimento ou a pasta Seguro_Empresarial_Desenvolvimento ao lado do repositório. A pasta pode ser alterada na barra lateral ou com BB_DATATHON_DADOS. O dicionário é lido antes do processamento; o importador preserva os originais e recusa sobrescrever um destino existente.

## Dados públicos já preparados

[references/](references/) contém snapshots públicos com fonte, período e metodologia: IBGE/PNAD 2021 (27 capitais), clima ERA5/Open-Meteo de 1996 a 2025 (dez municípios do pacote) e 673 classes CNAE extraídas da edição indicada da NR-4. Nenhum registro de cliente foi incluído nesses arquivos. O manifesto registra hashes das saídas e das entradas públicas em cache.

As referências funcionam offline durante a análise. Uma pasta local data/referencias tem precedência sobre references. A barra lateral, BB_DATATHON_REFERENCIAS ou --referencias permitem selecionar outra pasta. Municípios/CNAEs sem correspondência permanecem desconhecidos, com aviso e confiança reduzida.

Para baixar novamente e reconstruir os indicadores, sem APIs pagas:

    .\.venv\Scripts\python.exe scripts/preparar_referencias.py --dados "CAMINHO_DOS_CSVS"

Use --somente seguranca, clima ou nr4 para reconstruir uma referência. Downloads ficam em data/referencias/cache; consultas climáticas de 30 anos respeitam intervalo entre cidades. Em caso de limitação da fonte, execute novamente depois: os downloads já concluídos serão reutilizados. O cálculo dos índices usa referências locais; a consulta opcional por CEP acessa o ViaCEP.

A geocodificação automática desta versão valida os dez municípios/UFs do pacote. Outras localidades exigem coordenada pública validada e atualização do preparador. Não são usadas as coordenadas perturbadas dos estabelecimentos. Dados municipais não distinguem bairros ou ruas.

## Interface

Em **Consultar por CEP**, informe oito dígitos (com ou sem hífen). Apenas o CEP é enviado ao ViaCEP, com timeout e cache de até 24 horas. Município, UF e código IBGE vinculam os indicadores locais; bairro e logradouro são exibidos quando disponíveis. A tela informa abrangência municipal, fonte, período e ausência de referências. Não há inferência de criminalidade pelo CEP nem busca automática de novos indicadores para municípios sem cobertura.

Para calcular as quatro prioridades, marque a opção de combinar a localização com uma empresa cadastrada. Os valores e características dessa unidade continuam sendo necessários; o CEP sozinho não fornece patrimônio, folha ou vidros. Essa consulta não grava alterações nos CSVs nem nas exportações em lote. Ao mudar a localização, indicadores e fontes anteriores são descartados, inclusive se o novo município não possuir referência.

- Visão geral: quatro prioridades, planos, confiança e sensibilidade.
- Análise: busca por atividade, porte ou CNAE; decomposição, fontes e valores das nove coberturas.
- Comparação: dois estabelecimentos, com diferenças dos quatro índices.
- Simulação: patrimônio, segurança territorial hipotética, vidros e cenários climáticos alternativos.
- Regras: parâmetros JSON validados, restauração dos padrões e sensibilidade do corte de roubo.
- Exportação: templates completos e pacote de auditoria.

Os dados digitais originais continuam disponíveis na base; proteção cibernética não compõe um quinto índice de decisão nem é exportada como cobertura contratada.

## Confirmar dados de vidros e funcionários

O arquivo [examples/confirmacoes_modelo.csv](examples/confirmacoes_modelo.csv) permite informar, por empresa e unidade, presença de vidros, valor de reposição e funcionários locais. Campos são opcionais; confirmação contraditória ou valor inválido é rejeitado. Se a ausência de vidros for explicitamente informada, sua prioridade será zero. Sinais textuais de loja/galeria não comprovam vidraças.

## Execução em lote

    .\.venv\Scripts\python.exe cli.py --dados "CAMINHO_DESENVOLVIMENTO" --saida output/desenvolvimento
    .\.venv\Scripts\python.exe cli.py --dados "CAMINHO_TESTE" --saida output/teste

Opcionais: --referencias PASTA, --territorio CSV (compatibilidade do enriquecimento anterior), --confirmacoes CSV e --config JSON.

Saídas: os dois templates nas colunas originais, auditoria.json (quatro índices, nove necessidades de decisão, nove dimensionamentos e comparação dos planos) e manifesto.json (preferências, regras e hashes). Uma linha por empresa-estabelecimento no resultado; uma linha por cobertura fixa do plano escolhido no template de coberturas. A interface também fornece download em ZIP. Os CSVs são reproduzíveis com as mesmas entradas e parâmetros; a data do manifesto varia.

## Limitações

Leia [METODOLOGIA.md](METODOLOGIA.md). Não há histórico de sinistros, preços reais, caixa/reservas ou condições de aceitação confirmadas. Os pesos e cortes são hipóteses da equipe. A folha é indicador econômico, não valor de indenização; NR-4 é classificação ocupacional, não probabilidade de acidente. A referência territorial distribuída é uma proxy domiciliar de 2021; uma referência SSP preparada substitui sua definição nos municípios cobertos, com origem explícita. Vendaval representa vento e vento com chuva, sem medir granizo, tornado ou resistência do telhado.

Faixas são cenários de exposição para discutir proteção, não preços ou limites aprovados. O prédio não recebe valor de reconstrução inventado. Sem base defensável para RC ou vidros, a faixa fica explicitamente pendente. A aceitação contratual permanece condicional.

## Testes e organização

    .\.venv\Scripts\python.exe -m pytest -q

A suíte usa fixtures artificiais e referências públicas congeladas, sem rede nem dados privados. A CI testa Python 3.12 e 3.13. Testes cobrem quatro índices, dimensionamento, contraste território/patrimônio, NR-4, ausência de duplicação de funcionários, clima, fontes independentes, vidros, templates e interface.

Arquivos principais: processamento.py organiza os dados; referencias.py calcula indicadores públicos; motor_pontuacao.py calcula os quatro índices e dimensiona nove coberturas; recomendador.py escolhe o plano; exportacao.py gera arquivos; app.py apresenta a interface. Pesos e limites ficam em config_regras.json.

Configurações 0.1/0.2 não são compatíveis com o contrato 0.3: partir do novo JSON e revisar os parâmetros. A interface restaura o novo padrão ao detectar mudança de versão. Os antigos cortes de upgrade de 60/85 e ganho de 15% foram substituídos pela meta; o limiar de 60 permanece somente como sinalização informativa.

## Integração SSP

O importador inspirado na DevC aceita planilhas locais XLS/XLSX ou URLs HTTPS explícitas no manifesto. A planilha precisa ter uma linha exata de `Roubo em Comércio` e os doze meses. O sistema não presume que todos os estados publiquem o mesmo formato: outras categorias, abas ou layouts exigem um adaptador validado. Não faz descoberta automática de fontes nem possui agendamento de atualizações.

Copie [examples/manifesto_ssp.csv](examples/manifesto_ssp.csv) para uma pasta local em `data/`, indique arquivo ou URL, ano, código IBGE, região, número de estabelecimentos do mesmo período e fonte. Marque `cobertura_municipal_completa=SIM` apenas depois de verificar que as regiões cobrem o município, sem sobreposição. O exemplo contém um caminho ilustrativo e não representa dados baixados ou um denominador conhecido.

    .\.venv\Scripts\python.exe scripts/importar_ssp.py --manifesto data/manifesto_ssp.csv --ano 2025

A saída padrão é `data/referencias/seguranca_ssp.csv`. Nessa pasta local padrão, arquivos de clima, segurança IBGE e NR-4 que faltarem são lidos de `references/`, preservando os snapshots distribuídos. Pastas personalizadas continuam usando apenas seus próprios arquivos. URLs ficam em cache ao lado do manifesto; `--atualizar` baixa novamente. Fontes, SHA-256 dos arquivos e horário de preparo são conservados. Não há download durante a análise, exceto a consulta opcional ao ViaCEP. Para outra pasta, use `--saida PASTA_REFERENCIAS/seguranca_ssp.csv` e selecione essa pasta na interface.

A SSP substitui a segurança municipal apenas nos municípios presentes na sua saída; não altera clima ou NR-4. A consulta por CEP, a análise cadastrada e os lotes usam o mesmo cruzamento. Uma linha SSP indisponível fica com confiança zero e aviso, sem aproveitar silenciosamente outra definição de criminalidade. Nos municípios sem linha SSP, a referência IBGE existente continua disponível.

Taxa = soma de ocorrências / soma dos estabelecimentos × 1.000. Exposição relativa = taxa/(taxa + referência fixa), com referência inicial experimental de 100 por mil, alterável por `--referencia-taxa`. Não se recalibra a escala conforme os municípios consultados. Dados sem denominador ou ano incompleto permanecem indisponíveis; contagens são conservadas quando observadas. Taxa de ocorrências não é probabilidade, pois pode haver repetição no mesmo estabelecimento. A equivalência das definições entre fontes e a calibração continuam pendentes.

Exemplo de preferências no lote:

    .\.venv\Scripts\python.exe cli.py --dados "CAMINHO_DOS_CSVS" --meta 80 --indispensavel QUEBRA_DE_VIDROS --saida output/integracao

Implementação assistida por Codex. A equipe deve compreender e defender as hipóteses. Identidade visual própria, sem logotipos oficiais ou alegação de vínculo institucional.
