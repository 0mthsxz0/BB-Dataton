# Protege Empresa | BB Datathon

## Portal e formulário web

O diretório [frontend/](frontend/) contém a home, o Seguro Empresarial e um formulário integrado de sete etapas, sem campo CPF. A seleção econômica tem as 970 atividades do catálogo público, nomes por extenso e busca por lista, nome ou descrição do negócio, com sugestão de subatividade.

Para abrir: `cd frontend` e `npm run dev` (no PowerShell, `npm.cmd run dev`). Acesse http://localhost:4174/cotacao. Não há dependências npm a instalar. A busca é local; os dados preenchidos não são enviados à seguradora. Pagamento e conclusão são demonstrativos, sem emissão ou cobrança. Consulte [a documentação do formulário](frontend/docs/COTACAO.md) para fontes, testes e limites.

O formulário chama o motor Python local, com questionário e confirmações por estabelecimento. A seleção de cadastro já gera análise inicial sem respostas presumidas. Veja [as regras e a implementação do guia](frontend/docs/GUIA_ATUALIZADO.md).

Versão 0.4: combina os quatro índices multifatoriais contínuos (roubo/furto, vendaval, RC empregador e vidros) com seis heurísticas de preferência das coberturas comuns. O plano considera **dez necessidades**, meta padrão de **80% de aderência** e coberturas das quais o usuário **não abre mão**. Não converte os quatro índices em categorias de 25/55/85 pontos nem os multiplica novamente pelo patrimônio. As dez coberturas continuam dimensionadas e exportadas; não há preços nos arquivos do Datathon.

Aderência = pontos ponderados presentes no plano / pontos ponderados das dez necessidades. Escolhe-se o menor nível que atinge a meta e contém todas as indispensáveis. Índices de 70 ou mais exigem presença da cobertura na indicação automática; não podem ser diluídos por pesos das comuns. As preferências da barra lateral valem para todas as unidades da sessão e da exportação; ficam registradas na configuração e auditoria. Aderência mede presença no catálogo, não qualidade contratual, probabilidade ou garantia de indenização. Os seis valores heurísticos são explicitamente identificados; não são novos modelos físicos de sinistro.

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
- Análise: busca por atividade, porte ou CNAE; decomposição, fontes e valores das dez coberturas.
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

Saídas: os dois templates nas colunas originais, auditoria.json (quatro índices, dez necessidades de decisão, dez dimensionamentos e comparação dos planos) e manifesto.json (preferências, regras e hashes). Uma linha por empresa-estabelecimento no resultado; uma linha por cobertura fixa do plano escolhido no template de coberturas. A interface também fornece download em ZIP. Os CSVs são reproduzíveis com as mesmas entradas e parâmetros; a data do manifesto varia.

## Limitações

Leia [METODOLOGIA.md](METODOLOGIA.md). Não há histórico de sinistros, preços reais, caixa/reservas ou condições de aceitação confirmadas. Os pesos e cortes são hipóteses da equipe. A folha é indicador econômico, não valor de indenização; NR-4 é classificação ocupacional, não probabilidade de acidente. A proxy domiciliar de 2021 foi excluída do índice empresarial. Referências SSP só contribuem após os controles da política seguranca-1.0 e continuam experimentais; consulte [as regras de confiabilidade e a inspeção do Sinesp VDE 2025](CONFIABILIDADE_SEGURANCA.md). Vendaval representa vento e vento com chuva, sem medir granizo, tornado ou resistência do telhado.

Faixas são cenários de exposição para discutir proteção, não preços ou limites aprovados. O prédio não recebe valor de reconstrução inventado. Sem base defensável para RC ou vidros, a faixa fica explicitamente pendente. A aceitação contratual permanece condicional.

## Testes e organização

    .\.venv\Scripts\python.exe -m pytest -q

A suíte usa fixtures artificiais e referências públicas congeladas, sem rede nem dados privados. A CI testa Python 3.12 e 3.13. Testes cobrem quatro índices, dimensionamento, contraste território/patrimônio, NR-4, ausência de duplicação de funcionários, clima, fontes independentes, vidros, templates e interface.

Arquivos principais: processamento.py organiza os dados; referencias.py calcula indicadores públicos; motor_pontuacao.py calcula os quatro índices e dimensiona dez coberturas; recomendador.py escolhe o plano; exportacao.py gera arquivos; app.py apresenta a interface. Pesos e limites ficam em config_regras.json.

Configurações 0.1/0.2/0.3 não são compatíveis com o contrato 0.4: partir do novo JSON e revisar os parâmetros. A interface restaura o novo padrão ao detectar mudança de versão. Os antigos cortes de upgrade de 60/85 e ganho de 15% foram substituídos pela meta; o limiar de 60 permanece somente como sinalização informativa.

## Integração SSP

O importador inspirado na DevC aceita planilhas locais XLS/XLSX ou URLs HTTPS explícitas no manifesto. A planilha precisa ter uma linha exata de `Roubo em Comércio` e os doze meses. O sistema não presume que todos os estados publiquem o mesmo formato: outras categorias, abas ou layouts exigem um adaptador validado. Não faz descoberta automática de fontes nem possui agendamento de atualizações.

Copie [examples/manifesto_ssp.csv](examples/manifesto_ssp.csv) para uma pasta local em `data/`, indique arquivo ou URL, ano, código IBGE, região, número de estabelecimentos do mesmo período e fonte. Marque `cobertura_municipal_completa=SIM` apenas depois de verificar que as regiões cobrem o município, sem sobreposição. O exemplo contém um caminho ilustrativo e não representa dados baixados ou um denominador conhecido.

    .\.venv\Scripts\python.exe scripts/importar_ssp.py --manifesto data/manifesto_ssp.csv --ano 2025

A saída padrão é `data/referencias/seguranca_ssp.csv`. Nessa pasta local padrão, arquivos de clima, segurança IBGE e NR-4 que faltarem são lidos de `references/`, preservando os snapshots distribuídos. Pastas personalizadas continuam usando apenas seus próprios arquivos. URLs ficam em cache ao lado do manifesto; `--atualizar` baixa novamente. Fontes, SHA-256 dos arquivos e horário de preparo são conservados. O importador também gera um manifesto do snapshot; seu hash é conferido antes do uso. Não há download durante a análise, exceto a consulta opcional ao ViaCEP. Para outra pasta, use `--saida PASTA_REFERENCIAS/seguranca_ssp.csv` e selecione essa pasta na interface.

A SSP substitui a segurança municipal apenas nos municípios presentes na sua saída; não altera clima ou NR-4. A consulta por CEP, a análise cadastrada e os lotes usam o mesmo cruzamento. Uma linha SSP indisponível fica com confiança zero e aviso, sem aproveitar silenciosamente outra definição de criminalidade. Nos municípios sem linha SSP, a referência IBGE continua visível como dado histórico, sem contribuir para a pontuação empresarial.

Taxa = soma de ocorrências / soma dos estabelecimentos × 1.000. Exposição relativa = taxa/(taxa + referência fixa), com referência inicial experimental de 100 por mil, alterável por `--referencia-taxa`. Não se recalibra a escala conforme os municípios consultados. Dados sem denominador, sem sua fonte e ano, ou com ano incompleto permanecem indisponíveis; contagens são conservadas quando observadas. Preencha fonte_denominador e ano_denominador no manifesto; este último deve coincidir com o ano das ocorrências. Referências sem integridade conferida ou fora da validade de 24 meses após dezembro do ano observado não contribuem. Use --data-analise AAAA-MM-DD no lote para reproduzir a decisão de validade. Taxa de ocorrências não é probabilidade, pois pode haver repetição no mesmo estabelecimento. A equivalência das definições entre fontes e a calibração continuam pendentes.

Exemplo de preferências no lote:

    .\.venv\Scripts\python.exe cli.py --dados "CAMINHO_DOS_CSVS" --meta 80 --indispensavel QUEBRA_DE_VIDROS --saida output/integracao

Implementação assistida por Codex. A equipe deve compreender e defender as hipóteses. Identidade visual própria, sem logotipos oficiais ou alegação de vínculo institucional.

## Opcionais por exposição e duas jornadas

Execute `cd frontend` e `npm.cmd start` no Windows. A landing page (`/`) leva ao cadastro público (`/cotacao`), sem seleção de empresas. O painel de consultoria (`/interno`) permite consultar a base local com justificativas, evidências e alternativas. Ambos chamam o mesmo motor; o relatório público omite índices e dados técnicos de origem. O painel é uma demonstração local e precisa de autenticação/autorização antes de publicação em rede.

O mapa do guia contém 21 itens: quatro coberturas ajustáveis e 17 opcionais, incluindo quatro modalidades de lucro separadas. `opcionais.py` usa regras versionadas em `frontend/public/product-rules.json`, registra os sinais CSV disponíveis e as perguntas que precisam de confirmação. Indícios não confirmam exposição, campos vazios são desconhecidos e respostas negativas prevalecem. Nenhum adicional é incluído automaticamente; solicitar avaliação exige confirmação e plano compatível. Lucros permitem apenas uma modalidade por simulação. As assistências e seis coberturas obrigatórias são preservadas.

A comparação considera a meta e as lacunas dos dez itens padrão, acrescentando os opcionais pertinentes sem diluir prioridades críticas. Essencial + eletrônicos pode aparecer como alternativa; equipamento elétrico genérico não comprova eletrônico e este adicional não cobre roubo. Sem preços não há promessa de economia. As confirmações são mantidas em memória no navegador; não há persistência de leads nem emissão de proposta. Consulte `entregas/mapa-opcionais.md` e o fluxograma SVG.

Validação: `.venv/Scripts/python.exe -m pytest -q`, `npm.cmd --prefix frontend run check` e `npm.cmd --prefix frontend test`.

Na jornada pública, vidros são informados pela quantidade aproximada de janelas, portas, vitrines e espelhos, sem exigir orçamento de reposição. O motor registra a quantidade em campo separado, sem converter contagem em reais; o consultor conserva o campo financeiro e confirma o valor posteriormente. Quantidade vazia significa desconhecida; zero deve concordar com a ausência de vidros declarada.

As perguntas de proteção aparecem antes dos valores. A quantidade de empregados é coletada uma única vez no bloco do empregador e define a presença: zero = ausência, positivo = presença e vazio = desconhecido. Com zero, a pergunta de exposição ocupacional é dispensada; ao voltar a informar empregados, ela exige nova resposta.

## Pacote unificado e perfil da atividade

A recomendação reúne automaticamente no pacote as proteções compatíveis com o plano para operações confirmadas. Não inclui uma proteção quando a operação foi negada; recusas explícitas prevalecem. As modalidades de lucro continuam mutuamente exclusivas e exigem definição específica. A apresentação ao cliente usa uma lista única de coberturas, com o total calculado e a vigência real. Aceitação, preço e limites permanecem sujeitos à cotação oficial. O detalhamento técnico conserva a origem da composição para auditoria.

O código da atividade é coletado antes das perguntas e consulta `/api/cnae/perfil`. Ele não identifica uma empresa. Com pelo menos cinco empresas, o servidor produz medianas de sete valores financeiros; faturamento é agregado uma vez por empresa para não favorecer empresas com mais filiais. A interface identifica claramente a referência fictícia, deixa os valores editáveis e recolhe os campos preenchidos em uma seção de revisão. Não preenche condições físicas nem confirma operações por estatísticas do grupo. O servidor confere se cada valor marcado como estimado corresponde ao perfil consultado, registra a origem e reduz a confiança do inventário estimado. Alterar o código limpa as referências anteriores, preservando alterações manuais.

No painel interno, o cadastro vinculado preenche dados disponíveis da unidade e confirmações explicitamente registradas, sem transformar ausência de informação em resposta negativa. Palavras-chave das perguntas aparecem em destaque, e responsabilidade civil é escrita por extenso.

## Células de origem e confirmação dos dados

No relatório interno, “Origem e confirmação” diferencia o valor utilizado das células originais dos CSVs: arquivo, linha da tabela (incluindo cabeçalho), registro, campo, conteúdo original e significado resumido. Agregados patrimoniais mostram os bens e os pesos de vínculo que os formaram, com aviso para registros inválidos ou duplicados; valores substituídos no formulário conservam o cadastro apenas para comparação. A consulta limita as células à empresa/unidade vinculada e às colunas previstas; a contagem de unidades usa somente seus identificadores. A jornada pública não expõe registros individuais de outras empresas; perfis por atividade identificam a mediana e a amostra agregada.

Cada evidência explica por que precisa de confirmação, o que verificar e onde encontrar a informação (inventário, notas, contratos, contador ou vistoria, conforme o campo). Índices normalizados, pesos, confiança e proporções são apresentados em porcentagem; taxas por mil são divididas por dez para essa apresentação. Reais, quantidades, datas e classes ordinais mantêm suas unidades, e o conteúdo original é preservado para auditoria. A apresentação não altera as fórmulas nem transforma prioridades em probabilidades de sinistro.

## Voz personalizada no painel interno

No Windows, o modo trial gera o roteiro aprovado como áudio WAV mono de 16 kHz com a voz local Microsoft Maria Desktop, usando System.Speech. A Twilio recebe uma instrução Play para reproduzir esse arquivo. É necessário manter `servidor_voz.py` na porta 8765 e um túnel HTTPS ativo, com `TWILIO_TWIML_URL` terminado em `/voz.xml`. O servidor entrega somente os roteiros e áudios com identificadores temporários; ambos expiram após uma hora. Os arquivos ficam em `tmp/roteiros_voz`, ignorado pelo Git.

Antes de solicitar a ligação, o adaptador verifica se o roteiro público corresponde ao aprovado. Falha nessa verificação impede o envio à Twilio. Para usar a síntese de voz da Twilio no Windows, configure `BB_VOICE_PLAYBACK=say`; em outros sistemas esse caminho continua sendo o padrão. O modo completo usa TwiML diretamente.

Para consultar a última chamada sem realizar novas ligações, execute `python scripts/diagnosticar_voz.py` no terminal com as credenciais Twilio já configuradas. O script consulta o estado, notificações e eventos disponíveis sem exibir credenciais ou telefones. Também aceita um Call SID como argumento. A entrega do XML ou do áudio por HTTP não comprova a reprodução no telefone; confirme a audição em um teste autorizado.
