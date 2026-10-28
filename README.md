# Protege Empresa | BB Datathon

Versão 0.2: escolha de plano baseada em **quatro índices**: roubo/furto, vendaval, responsabilidade civil empregador e quebra de vidros. As cinco coberturas comuns são dimensionadas e exportadas, sem pontuação na decisão. Prioridade maior significa maior atenção recomendada, nunca probabilidade de sinistro.

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

Saídas: os dois templates nas colunas originais, auditoria.json (quatro índices, nove dimensionamentos e comparação dos planos) e manifesto.json (regras e hashes). Uma linha por empresa-estabelecimento no resultado; uma linha por cobertura fixa do plano escolhido no template de coberturas. A interface também fornece download em ZIP. Os CSVs são reproduzíveis com as mesmas entradas e parâmetros; a data do manifesto varia.

## Limitações

Leia [METODOLOGIA.md](METODOLOGIA.md). Não há histórico de sinistros, preços reais, caixa/reservas ou condições de aceitação confirmadas. Os pesos e cortes são hipóteses da equipe. A folha é indicador econômico, não valor de indenização; NR-4 é classificação ocupacional, não probabilidade de acidente. O índice territorial é uma proxy domiciliar de 2021. Vendaval representa vento e vento com chuva, sem medir granizo, tornado ou resistência do telhado.

Faixas são cenários de exposição para discutir proteção, não preços ou limites aprovados. O prédio não recebe valor de reconstrução inventado. Sem base defensável para RC ou vidros, a faixa fica explicitamente pendente. A aceitação contratual permanece condicional.

## Testes e organização

    .\.venv\Scripts\python.exe -m pytest -q

A suíte usa fixtures artificiais e referências públicas congeladas, sem rede nem dados privados. A CI testa Python 3.12 e 3.13. Testes cobrem quatro índices, dimensionamento, contraste território/patrimônio, NR-4, ausência de duplicação de funcionários, clima, fontes independentes, vidros, templates e interface.

Arquivos principais: processamento.py organiza os dados; referencias.py calcula indicadores públicos; motor_pontuacao.py calcula os quatro índices e dimensiona nove coberturas; recomendador.py escolhe o plano; exportacao.py gera arquivos; app.py apresenta a interface. Pesos e limites ficam em config_regras.json.

Configurações 0.1 não são compatíveis com o contrato 0.2: partir do novo JSON e revisar os parâmetros. A interface restaura o novo padrão ao detectar mudança de versão.

Implementação assistida por Codex. A equipe deve compreender e defender as hipóteses. Identidade visual própria, sem logotipos oficiais ou alegação de vínculo institucional.
