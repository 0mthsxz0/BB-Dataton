# Protege Empresa | BB Datathon

Aplicação acadêmica para analisar necessidades de proteção de empresas e estabelecimentos. Combina risco relativo do evento, impacto financeiro, vulnerabilidade operacional e interações específicas de cada cobertura. Nenhuma nota representa probabilidade de sinistro ou parâmetro oficial da seguradora.

## Executar

Python 3.12 ou 3.13. No Windows/PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/importar_dados.py "CAMINHO\Seguro_Empresarial_Desenvolvimento"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

No Linux/macOS, use `.venv/bin/python` no lugar de `.\.venv\Scripts\python.exe`.

Abra o endereço apresentado pelo Streamlit, normalmente `http://localhost:8501`. A aplicação também reconhece a pasta `Seguro_Empresarial_Desenvolvimento` ao lado do repositório. A fonte pode ser alterada na barra lateral ou pela variável `BB_DATATHON_DADOS`.

Para reproduzir exatamente as versões instaladas na validação local com Python 3.12, substitua `requirements.txt` por `requirements-lock.txt` no comando de instalação. A integração contínua também verifica compatibilidade com Python 3.13.

Os arquivos originais não são publicados no Git. Obtenha os nove CSVs fornecidos pela organização:

```text
empresas.csv
enderecos_estabelecimentos.csv
sinais_financeiros_operacionais.csv
bens_cadastrados.csv
territorio.csv
catalogo_coberturas_fixas_planos.csv
dicionario_dados.csv
template_resultado_times.csv
template_coberturas_times.csv
```

O script de importação copia os arquivos, preserva a origem e recusa sobrescrever uma pasta já existente. O dicionário é lido antes do processamento.

## Processar e exportar sem interface

```powershell
.\.venv\Scripts\python.exe cli.py --dados "CAMINHO\Seguro_Empresarial_Desenvolvimento" --saida output/desenvolvimento
.\.venv\Scripts\python.exe cli.py --dados "CAMINHO\Seguro_Empresarial_Teste_Comum" --saida output/teste
```

Saídas:

- `template_resultado_times.csv`: uma linha por empresa-estabelecimento, nas colunas originais.
- `template_coberturas_times.csv`: todas as coberturas fixas do plano sugerido, uma linha por cobertura/unidade.
- `auditoria.json`: fatores, transformações, decomposição, incertezas e comparação dos planos.
- `manifesto.json`: configuração completa e hashes SHA-256 das entradas, regras e CSVs de saída.

As notas são calculadas sem arredondamento intermediário. Com as mesmas entradas e regras, os CSVs são reproduzíveis. A data do manifesto muda a cada execução.

## Interface

- **Visão geral:** empresas, estabelecimentos, distribuição de planos, prioridades e confiança.
- **Análise:** busca por ID/CNAE, atividade e porte; gráficos, fatores e fórmulas por cobertura.
- **Comparação:** duas unidades lado a lado e diferenças de pontuação.
- **Simulação:** alteração dos valores dos bens, dependência digital e indicador territorial hipotético, sem alterar os originais.
- **Regras:** edição e validação do JSON, restauração dos padrões e sensibilidade do corte de roubo.
- **Exportação:** download dos templates e pacote ZIP com auditoria.

Identidade visual própria em azul e amarelo. Sem logotipos oficiais ou alegação de vínculo institucional.

## Modelo e suas limitações

Leia [METODOLOGIA.md](METODOLOGIA.md) para as fórmulas, justificativas dos pesos, interações e critérios de aceitação.

O motor cobre as nove proteções do catálogo oficial fornecido e calcula, separadamente, uma necessidade adicional de avaliação cibernética. Assistência digital não é tratada como seguro cibernético. Nenhuma cobertura adicional é exportada como disponível/contratada sem confirmação documental.

Não há histórico de sinistros, preços reais, caixa/reservas, valor do prédio ou inventário de vidros. A versão inicial usa cenários financeiros e proxies explicitamente identificadas. Em RC e vidros, a faixa monetária fica excepcionalmente sem valor, com justificativa, quando não existe base defensável. Não gera indenizações fictícias a partir de faturamento ou área.

Elegibilidade é uma triagem preliminar. Aceitação de atividade e condições contratuais estão pendentes por padrão; recomendações continuam disponíveis como sugestões condicionais. Imóveis em obra, irregulares ou com materiais de construção a validar geram pendências. A ausência de aluguel não comprova imóvel próprio.

As médias e distribuições das recomendações avaliam o comportamento do protótipo. Não medem precisão preditiva ou adequação atuarial.

## Enriquecimento territorial opcional

O CSV original não traz índices de segurança ou clima. O sistema funciona sem dados externos, mostra a ausência e reduz a confiança. Não inventa índices pela latitude/longitude.

Use [examples/territorio_modelo.csv](examples/territorio_modelo.csv) como cabeçalho. Para segurança, preencha `codigo_ibge_municipio`, `seguranca_da_cidade_0_1`, `fonte`, `ano_referencia`, `granularidade` (MUNICIPIO), `metodologia` e `confianca_territorial_0_1`. Para clima, use `exposicao_climatica_0_1`. Remova a coluna de indicador que não tiver dados. Uma linha por município; índices entre 0 e 1.

```powershell
.\.venv\Scripts\python.exe cli.py --dados "CAMINHO_DOS_CSVS" --territorio "territorio_documentado.csv"
```

Pode-se integrar um índice experimental derivado de dados públicos, como a pesquisa de vitimização do [IBGE](https://www.ibge.gov.br/comunicados/35373-ibge-divulgara-em-7-de-dezembro-a-pesquisa-nacional-por-amostra-de-domicilios-continua-vitimizacao-furto-e-roubo-2021.html). Verifique universo, unidades, denominadores, amostragem e disponibilidade geográfica. Uma medida domiciliar de 2021 não é taxa atual de roubos empresariais. A normalização, fonte e referência devem ser documentadas. Esta versão fornece o importador validado; não inclui índices calculados por terceiros nem um downloader SIDRA.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Testes de coerência financeira, patrimônio versus evento, digital, vidros, incerteza, duplicações, vínculos, múltiplas unidades, decisão de planos, esquema dos templates, reprodutibilidade e navegação/exportação no Streamlit. Fixtures artificiais são usadas exclusivamente nos testes. A integração contínua executa a suíte sem depender dos CSVs privados.

## Organização

```text
app.py                   Interface Streamlit
processamento.py         CSVs, validações, vínculos e bens por unidade
motor_pontuacao.py        Evento × impacto × vulnerabilidade + interações
recomendador.py          Comparação de planos e elegibilidade preliminar
exportacao.py            Templates, auditoria e manifesto
cli.py                   Execução em lote
config_regras.json       Hipóteses, mapas, pesos e limites
scripts/importar_dados.py Importação local dos originais
tests/                   Testes independentes dos dados privados
```

Uso de IA: implementação assistida por Codex. A equipe deve revisar, compreender e defender as hipóteses. Antes de utilização comercial, validar regras, aceitação, coberturas, valores, preços e resultados com especialistas e documentação contratual vigente.
