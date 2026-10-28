# Relatório do sistema — Protege Empresa

**Projeto:** recomendação de seguros empresariais para o BB Datathon
**Versão analisada:** 0.3.0
**Data:** 28 de outubro de 2026
**Referência do código:** commit `b247615` do repositório BB-Dataton
**Natureza:** protótipo acadêmico com dados empresariais fictícios.

## 1. Objetivo

O sistema organiza informações de uma empresa e de seus estabelecimentos, identifica necessidades de proteção e sugere um dos planos do catálogo: Essencial, Prático ou Total. A recomendação apresenta as informações utilizadas, as regras aplicadas e as limitações dos dados.

O resultado apoia a análise de seguros. Não constitui contratação, cotação oficial ou aprovação de aceitação pela seguradora. Os cálculos são determinísticos e configuráveis: os mesmos dados, referências e parâmetros produzem os mesmos resultados de pontuação. Não há modelo de aprendizado de máquina treinado com sinistros.

## 2. Funcionamento geral

O fluxo principal segue estas etapas:

1. Ler e validar os arquivos do Datathon e seu dicionário de dados.
2. Organizar uma linha por estabelecimento, preservando a relação com a empresa.
3. Calcular valores dos bens associados ao local e incorporar referências públicas disponíveis.
4. Calcular quatro índices multifatoriais de proteção.
5. Acrescentar cinco pontuações heurísticas das coberturas comuns.
6. Comparar os planos pelas nove necessidades, pela meta de aderência e pelas proteções indispensáveis.
7. Apresentar explicações, incertezas e cenários de valores; permitir exportação.

Empresa e estabelecimento são tratados como níveis diferentes. Por exemplo, o sistema não divide arbitrariamente o faturamento da empresa entre filiais nem multiplica a folha local pelo número total de funcionários.

## 3. Informações utilizadas

Os nove arquivos de entrada são:

| Arquivo | Finalidade |
|---|---|
| empresas.csv | Identificação, atividade, porte e informações empresariais |
| enderecos_estabelecimentos.csv | Unidades, município, código IBGE e características cadastradas |
| sinais_financeiros_operacionais.csv | Folha, estoques, despesas, aluguel e sinais operacionais |
| bens_cadastrados.csv | Bens, valores e vínculo estimado com os estabelecimentos |
| territorio.csv | Vínculos e informações territoriais do pacote |
| catalogo_coberturas_fixas_planos.csv | Coberturas presentes em cada plano |
| dicionario_dados.csv | Descrição dos campos fornecidos |
| template_resultado_times.csv | Estrutura de saída por estabelecimento |
| template_coberturas_times.csv | Estrutura de saída por cobertura |

O valor ponderado de cada bem é recalculado como **valor cadastrado × probabilidade de estar no imóvel**, uma única vez. Cadastros conflitantes e vínculos inválidos são rejeitados. Informação ausente não é automaticamente interpretada como valor zero ou ausência de risco.

As referências distribuídas incluem segurança contextual do IBGE/PNAD de 2021 para 27 capitais, clima ERA5/Open-Meteo de 1996 a 2025 para dez municípios e 673 classes CNAE extraídas da edição indicada de 2023 da NR-4. As fontes e versões ficam identificadas nos arquivos. A referência ocupacional é contextual; o sistema não certifica a vigência ou aplicabilidade jurídica da classificação.

## 4. Quatro índices multifatoriais

O motor separa três dimensões:

| Componente | Significado |
|---|---|
| Evento — R | Exposição relativa ao evento, conforme a evidência disponível |
| Impacto — I | Escala financeira ou econômica associada à perda |
| Vulnerabilidade — V | Aproximação da capacidade de suportar a perda ou da suscetibilidade física |

Essa separação evita afirmar que uma empresa tem maior probabilidade de ser roubada simplesmente porque possui patrimônio maior. O patrimônio afeta principalmente o impacto. Também evita que uma localização mais segura elimine automaticamente a relevância de uma perda elevada.

A fórmula geral é:

```text
P = 100 × limitar[
      (0,25 + 0,75 × I)
    × (0,20 + 0,80 × R)
    × (0,70 + 0,30 × V)
    + k × I × R × D
    , 0, 1]
```

`P` varia de 0 a 100. `D` representa uma interação específica e `k` seu coeficiente. Na configuração atual, o termo adicional é utilizado para vidros; nas demais três coberturas, o coeficiente é zero. A interação entre R, I e V permanece presente pela multiplicação dos componentes.

Os pisos e coeficientes são hipóteses de triagem da equipe. Não são probabilidades mínimas nem parâmetros oficiais da seguradora. A normalização monetária usa uma transformação logarítmica com referências fixas, limitada a 1, preservando o valor bruto para consulta.

### Roubo, furto e arrombamento

O evento relativo usa o complemento da segurança municipal disponível. A referência distribuída é uma proxy de vitimização domiciliar; uma referência SSP preparada pode substituí-la nos municípios cobertos. O impacto considera bens ponderados e estoque médio. O estoque de pico participa dos cenários de exposição, sem ser somado novamente ao estoque médio.

O índice territorial não demonstra uma probabilidade de roubo da empresa. Fontes com definições diferentes permanecem identificadas e exigem revisão antes de comparação.

### Vendaval e eventos correlatos

O evento utiliza o indicador climático municipal preparado a partir de frequências históricas de rajadas e combinação de vento com chuva. O impacto considera conteúdo e estoque. A vulnerabilidade combina aproximações financeiras e padrão construtivo.

Os dados não representam uma medição no imóvel nem uma avaliação da resistência do telhado. Também não estimam individualmente todos os eventos incluídos no nome contratual da cobertura.

### Responsabilidade civil do empregador

O evento contextual parte da classe CNAE e do grau ocupacional da NR-4, com o mapa experimental: grau 1 = 0,25; grau 2 = 0,50; grau 3 = 0,75; grau 4 = 1,00. A folha mensal local é normalizada com referência de R$ 500 mil e usada como aproximação econômica do impacto.

A quantidade empresarial de funcionários não multiplica novamente a folha. O grau não é uma taxa de acidentes, e a folha não é convertida em indenização. O sistema mantém pendente uma faixa monetária sem base defensável.

### Quebra de vidros

O modelo utiliza sinais de loja/galeria e atividade como aproximações, permitindo confirmação da presença dos vidros e de seu valor de reposição. A área do imóvel, isoladamente, não comprova quantidade ou valor dos vidros. A confirmação explícita de ausência resulta em prioridade zero para essa exposição.

## 5. Cinco necessidades comuns

Além dos quatro índices, o sistema calcula cinco preferências experimentais para a comparação dos planos:

| Cobertura | Pontuação inicial |
|---|---|
| Incêndio, raio, explosão e fumaça | 70 com inventário; 50 sem inventário |
| Danos elétricos | 30 + 60 × dependência tecnológica normalizada |
| Perda ou pagamento de aluguel | 75 com pagamento recorrente; 25 sem o sinal |
| RC estabelecimento | 70 com sinal de loja/galeria; 50 sem o sinal |
| Despesas fixas | 30 + 60 × despesa mensal / (despesa mensal + 30.000) |

Esses pontos são identificados como **heurísticas de preferência**. Não são cinco novos modelos de frequência e severidade de sinistros. Quando falta um sinal necessário, a regra utiliza ponto central de desconhecimento e confiança zero, conforme a metodologia.

Assim, existem **quatro índices multifatoriais, nove necessidades para decidir o plano e nove dimensionamentos de cobertura**. Os quatro índices entram na decisão com notas contínuas; não são convertidos em apenas 25, 55 ou 85 pontos.

## 6. Seleção do plano

O catálogo utilizado tem a seguinte composição:

| Plano | Composição |
|---|---|
| Essencial | As cinco coberturas comuns |
| Prático | Essencial + roubo/furto/arrombamento + vendaval |
| Total | Prático + RC empregador + quebra de vidros |

A comparação usa:

```text
Aderência = 100 × soma(peso × pontos das coberturas presentes)
                  ÷ soma(peso × pontos das nove necessidades)
```

A meta padrão é **80%**, com pesos iniciais iguais a 1. O sistema escolhe o menor nível do catálogo que alcança a meta e contém todas as coberturas marcadas em **“Não abrir mão”**. Essa exigência continua valendo mesmo quando a cobertura tem pontuação zero.

As preferências da barra lateral valem para as unidades analisadas e para todas as unidades da exportação daquela sessão. Elas ficam registradas na configuração e na auditoria. Os valores das cinco comuns agora influenciam o denominador, conforme a escolha de integração solicitada.

Uma aderência de 100% no Total significa presença das nove coberturas consideradas no catálogo. Não significa que qualquer perda esteja integralmente protegida. Preços, limites contratados, franquias e exclusões não compõem essa conta. Os arquivos do Datathon não disponibilizam preços, portanto o sistema não calcula prêmio nem afirma escolher o seguro mais barato.

## 7. Localização por CEP

Na consulta opcional, o sistema envia apenas o CEP ao ViaCEP e obtém município, UF, código IBGE e, quando disponíveis, bairro e logradouro. A resposta é validada e pode ser mantida em cache por até 24 horas. CEP inválido, não encontrado e falha de comunicação são tratados.

O código IBGE conecta a localização às referências locais. A abrangência atual é **municipal**: um bairro informado no endereço não torna o índice específico daquele bairro. Para calcular prioridades, ainda são necessários os dados empresariais; o CEP sozinho não informa patrimônio, estoque, folha ou vidros.

A consulta pode combinar a nova localização com uma unidade cadastrada sem gravar mudanças nos arquivos originais. Ao mudar o município, referências anteriores são removidas para impedir o reaproveitamento indevido de índices da cidade antiga.

## 8. Integração de segurança pública — SSP

O importador aceita planilhas locais XLS/XLSX ou URLs HTTPS explicitamente cadastradas em um manifesto. O formato suportado exige uma linha de Roubo em Comércio e os doze meses. Outros layouts estaduais podem exigir adaptadores.

Para produzir o indicador, são necessários código IBGE, ano, origem, contagens, denominador de estabelecimentos e confirmação de que a cobertura territorial é completa e sem sobreposição. A consolidação usa:

```text
Taxa = soma das ocorrências / soma dos estabelecimentos × 1.000
Risco relativo SSP = taxa / (taxa + referência fixa)
Segurança relativa SSP = 1 − risco relativo SSP
```

A referência inicial é experimental: 100 ocorrências por mil estabelecimentos. Ela é configurável e não se recalibra conforme o subconjunto consultado. Uma taxa de ocorrências não representa probabilidade, pois pode haver repetição no mesmo estabelecimento.

Foram corrigidos os problemas identificados na DevC: conversão numérica que alterava valores, média simples de taxas regionais, transformação de ausência em zero e incompatibilidade na seleção de períodos. O importador também recusa duplicações e certas combinações explícitas de total municipal com regiões.

Downloads utilizam cache; uma opção permite atualização deliberada. Fontes, hashes e horário de preparo do indicador são conservados. O preparo não comprova a data de atualização do portal original. A análise cadastral, o CEP e os lotes usam a mesma referência preparada. Clima e NR-4 são preservados.

**Situação atual:** o importador está integrado, mas a validação 0.3 não acrescentou uma base SSP real. Sua alimentação depende de arquivos ou URLs compatíveis e do denominador adequado. Não há descoberta automática de todos os portais, atualização agendada ou diferenciação por região administrativa. Indicadores incompletos permanecem indisponíveis, com confiança zero.

## 9. Confiança, incerteza e dimensionamento

Nos quatro índices, a confiança reflete a qualidade contextual dos componentes. Nas cinco heurísticas, são utilizadas confianças conservadoras documentadas. A confiança geral é uma média ponderada das nove necessidades. Ela não é percentual de acerto.

O sistema calcula faixas de sensibilidade. Na aderência, os extremos consideram tanto as coberturas presentes quanto as ausentes, pois o resultado é uma razão. A faixa é conservadora e não constitui intervalo estatístico. A recomendação é sinalizada quando pode mudar dentro desses cenários.

O dimensionamento financeiro permanece separado da pontuação. São apresentados cenários para bens, equipamentos, aluguel e despesas de paralisação, sem inventar valor de reconstrução do prédio. Para RC ou vidros sem evidência suficiente, os valores ficam pendentes. As faixas não são preços nem limites contratuais aprovados.

## 10. Tecnologias e organização

| Tecnologia ou módulo | Uso |
|---|---|
| Python | Processamento e regras determinísticas |
| pandas e NumPy | Organização e tratamento dos dados |
| Streamlit e Plotly | Painel analítico, gráficos e simulações |
| requests | Consulta de CEP e downloads explícitos dos preparadores |
| openpyxl e xlrd | Leitura de planilhas SSP |
| pypdf | Extração da referência ocupacional em PDF |
| pytest e testes de interface | Verificação automatizada |
| GitHub Actions | Configuração de testes para Python 3.12 e 3.13 |
| CSV, JSON e SHA-256 | Entradas, saídas e rastreabilidade |

Os principais arquivos são processamento.py, motor_pontuacao.py, recomendador.py, localizacao.py, territorio_ssp.py, exportacao.py, app.py e config_regras.json. A execução em lote é oferecida por cli.py.

Existe também um portal demonstrativo separado em frontend/, com HTML, CSS, JavaScript e servidor Node.js local. Ele inclui formulário de cotação demonstrativo e busca de atividades. Esse formulário não está conectado ao motor Python e não realiza emissão, cobrança ou envio à seguradora. O painel funcional de análise é o Streamlit, normalmente na porta 8501.

## 11. Exportação e auditoria

O sistema gera os dois templates CSV nas colunas originais, uma auditoria JSON e um manifesto de configuração e hashes. A auditoria distingue os quatro índices, as nove necessidades de decisão, os nove dimensionamentos e a comparação dos planos. O painel permite baixar um pacote ZIP; a linha de comando processa a base completa.

Os dados empresariais originais e as saídas locais não são publicados no Git. O cálculo usa snapshots locais; acessos externos ocorrem na consulta opcional ao CEP e nos preparadores acionados. Não há integração com contas bancárias reais.

## 12. Validação registrada

A validação local da versão 0.3 passou em **93 testes automatizados**, incluindo consistência de fórmulas, cenários financeiros contrastantes, incerteza, meta, indispensáveis, CEP, SSP, interface e exportação. Esse resultado é o registrado em VALIDACAO_0_3.md; este relatório não representa uma nova execução da suíte nem confirma um resultado remoto da CI.

Também foram processadas as duas bases completas, com meta de 80%, sem indispensáveis e com as referências públicas disponíveis:

| Resultado | Desenvolvimento | Teste comum |
|---|---:|---:|
| Estabelecimentos | 2.978 | 144 |
| Essencial | 71 | 2 |
| Prático | 2.852 | 136 |
| Total | 55 | 6 |
| Linhas exportadas de coberturas | 20.814 | 1.016 |

No total, foram processados **3.122 estabelecimentos**. Foram verificadas as chaves, a ausência de duplicações nas saídas e a correspondência entre plano e coberturas. No navegador, a unidade de exemplo passou de Prático para Total ao exigir vidros, mantendo as notas dos quatro índices.

Os testes SSP usaram planilhas sintéticas e downloads simulados. Os números acima não demonstram precisão preditiva, recomendação comercial correta ou distribuição ideal dos planos.

## 13. Limitações e evolução

O sistema ainda não tem histórico de sinistros para calibração atuarial, preços reais, reservas de caixa, inventário completo de vidros, valor de reconstrução do prédio ou validação contratual completa. As referências territoriais são municipais e possuem períodos e definições próprios. A classificação NR-4 não comprova acidente ou responsabilidade jurídica.

Os próximos passos recomendados são validar os pesos e a meta com a equipe e especialistas; alimentar o SSP com fontes comparáveis e denominadores revisados; melhorar dados locais de vulnerabilidade e reposição; conectar o formulário ao motor; e avaliar limites, franquias, elegibilidade e requisitos de produção antes de qualquer uso real.

O estágio atual é de **MVP funcional para demonstração e avaliação acadêmica**, com processamento verificável e limitações explícitas. A validação realizada comprova coerência computacional dos casos testados, sem substituir avaliação atuarial ou contratual.

## 14. Documentos de apoio

- README.md: instalação, uso e alimentação das referências.
- METODOLOGIA.md: fórmulas, hipóteses e tratamento de incerteza.
- VALIDACAO_0_3.md: testes e resultados registrados da integração.
- config_regras.json: parâmetros da versão 0.3.0.
- examples/manifesto_ssp.csv: modelo ilustrativo para alimentar o importador SSP.
