# Base municipal de segurança

Branch: `dados-de-seguranca`, derivada de `codex/formulario-cotacao-busca-inteligente`.

O módulo `seguranca/` reúne coleta, importação, banco SQLite, índice relativo de
roubo, exportação CSV e consulta para o formulário. Não contém dados simulados na
base operacional. Fixtures artificiais existem somente em testes temporários.

## Situação da coleta

Atualização: [a hierarquia de fontes](HIERARQUIA_FONTES.md) já seleciona ocorrências
municipais reais do ISP-RJ e da SSP-RS. O texto abaixo preserva o diagnóstico da
coleta VDE/IBGE; os dados estaduais complementares têm proveniência separada.

Coleta retomada em 28/10/2026 no ambiente local Windows. IBGE e o download direto
do VDE 2025 responderam; o portal pode devolver 403 e o cliente Python apresentou
falha TLS no MJ. O GET com `curl.exe`, mantendo validação TLS, concluiu os 26.644.100
bytes; o SHA-256 coincide com a auditoria anterior. Não foi necessário mudar
permissões ou desligar validação de certificado.

O SQLite contém 5.571 localidades do cadastro IBGE, população estimada de 2025,
área censitária de 2022 quando disponível, os 69.510 registros originais do recorte
de roubos do VDE e os identificadores/códigos dos 2.978 estabelecimentos.
**A cobertura geográfica dos estabelecimentos é 100%; a cobertura do índice municipal é 0%.**

A inspeção real mostrou que veículo, carga e instituição financeira estão sem
município, mesmo com abrangência `Estadual`. Latrocínio está em `total_vitima`,
com `total` vazio. A fonte não contém roubo em comércio. Portanto não há série
municipal de ocorrências compatível com os quatro critérios: pesos CRITIC, índice
e ranking permanecem indisponíveis. Os CSVs reais expressam essa ausência com
índice vazio, nunca zero. Consulte [o relatório da validação real](VALIDACAO_SEGURANCA_2025.md).

## Fontes

- Portal oficial SINESP/MJ:
  https://www.gov.br/mj/pt-br/assuntos/sua-seguranca/seguranca-publica/estatistica
- Cadastro IBGE de municípios, com código de sete dígitos e UF:
  https://servicodados.ibge.gov.br/api/v1/localidades/municipios
- Censo 2022, agregado 4714, variáveis 93 (população) e 6318 (área):
  https://servicodados.ibge.gov.br/api/v3/agregados/4714/periodos/2022/variaveis/93%7C6318?localidades=N6[all]
- CRITIC: Diakoulaki, Mavrotas e Papayannakis (1995), *Determining objective
  weights in multiple criteria problems: The CRITIC method*, Computers &
  Operations Research 22(7), 763–770, DOI `10.1016/0305-0548(94)00059-H`.

A importação censitária preserva população e área de 2022. Neste snapshot, a
população foi substituída explicitamente pela estimativa oficial de 2025
(agregado 6579, variável 9324), com igualdade dos conjuntos de códigos do cadastro.
A área continua censitária de 2022 e seu ano aparece no CSV. Senatran não foi
incorporada; população continua sendo o denominador do método proposto.

## Instalação e execução

Use o checkout da branch `dados-de-seguranca`. Python 3.12,
dependências de `requirements-lock.txt` e Node >=20 são suficientes. Não há
dependências npm adicionais. Exemplo com o ambiente preparado:

```bash
cd /workspace/BB-Dataton
export BB_PYTHON=/workspace/.venvs/bb-dataton/bin/python
"$BB_PYTHON" -m seguranca iniciar
"$BB_PYTHON" -m seguranca baixar
```

O coletor percorre links do portal estatístico até três níveis e 40 páginas,
inventaria os documentos e baixa aqueles identificados como municipais no
link/contexto. Faz cache com SHA-256, URL, data e tamanho; preserva validação TLS.
O inventário inclui erros e indica limite de páginas atingido. Uma execução sem
documentos, com falhas ou truncada retorna código 2. Documentos via Power BI,
JavaScript ou links não publicados não são presumidos como coletados.

Os arquivos vão para `data/seguranca/fontes/`, fora do versionamento. PDFs e
dicionários ficam disponíveis para conferência; o importador aceita CSV/XLS/XLSX.
ZIPs precisam ser inspecionados antes de extrair: não há extração automática de
caminhos potencialmente inseguros. Para uma página municipal específica, use
`baixar --pagina-sinesp URL_OFICIAL`. Confirme o escopo, a periodicidade, a unidade
e a separação de naturezas no dicionário antes de importar.

```bash
"$BB_PYTHON" -m seguranca importar-ibge \
  --localidades data/seguranca/fontes/ibge/ibge_municipios.json \
  --indicadores data/seguranca/fontes/ibge/ibge_censo_2022.json
"$BB_PYTHON" -m seguranca inspecionar CAMINHO_DO_ARQUIVO_SINESP.xlsx
"$BB_PYTHON" -m seguranca importar-sinesp CAMINHO_DO_ARQUIVO_SINESP.xlsx \
  --url URL_OFICIAL_ORIGINAL_DO_ARQUIVO
"$BB_PYTHON" -m seguranca resumo
"$BB_PYTHON" -m seguranca gerar-indice --fim AAAA-MM
"$BB_PYTHON" -m seguranca consultar --codigo 3550308
"$BB_PYTHON" -m seguranca consultar --uf SP --busca 'São Paulo'
```

`AAAA-MM`, os caminhos e as URLs acima são parâmetros a preencher após a coleta,
não nomes de arquivos supostamente baixados. Omitir `--fim` usa o último mês
publicado entre os crimes selecionados e informa a defasagem em relação ao último
mês civil encerrado. Isso não transforma uma série antiga em dados atuais.

## Importação e auditoria

- A chave mensal é `(codigo_ibge, crime, mes)`. O código é texto de sete dígitos.
  Sem código, aceita-se somente correspondência exata normalizada de nome + UF
  no cadastro oficial. Não há junção por nome isolado nem aproximação automática.
- Reconhece cabeçalhos em português, meses em linhas ou em colunas e cabeçalho
  Excel deslocado até 20 linhas. Relata as folhas importadas e ignoradas.
- Colunas ambíguas exigem um JSON passado por `--mapa`. Exemplo:
  `{"codigo":"COD_IBGE","ano":"ANO","mes":"MES","crime":"NATUREZA","ocorrencias":"TOTAL"}`.
  Só mapear `TOTAL` depois de confirmar que mede ocorrências, não vítimas.
- Campo vazio, `-` ou `...` é ausência; zero explícito é observação válida.
  Não se divide total anual por 12, nem se infere zero de linha ausente.
- Contagens negativas/fracionárias, divergências de código/nome/UF e municípios
  desconhecidos ficam em `rejeicoes`, com fonte, folha, linha, motivo e conteúdo.
  Importação parcial retorna código 2. Investigue essas linhas antes de usar o índice.
- Duplicata mensal dentro do arquivo e valores conflitantes entre arquivos
  abortam a transação inteira. Não se somam dimensões desconhecidas. Sobreposição
  idêntica entre arquivos mantém vínculos com ambas as fontes sem duplicar a contagem.
- Revisões históricas com contagens diferentes exigem decisão explícita: esta
  versão não sobrescreve automaticamente a série anterior. Use novo banco para
  comparar versões antes de substituir a versão usada pelo formulário.
- Nova importação invalida os índices no SQLite; regenere as exportações depois.
  Não reutilize um CSV anterior como se tivesse sido atualizado pela importação.

Tabelas: `fontes`, `municipios`, `ocorrencias`, `ocorrencia_fontes`, `rejeicoes`,
`execucoes`, `indices`; view `consulta_municipal`. SQLite pode ser consultado por
qualquer cliente SQL, ou pela biblioteca `sqlite3` do Python em modo somente leitura:

```sql
SELECT uf, count(*) AS municipios, count(indice_roubo_0_100) AS com_indice
FROM consulta_municipal GROUP BY uf;

SELECT codigo_ibge, municipio, uf, indice_roubo_0_100, faixa, confianca
FROM consulta_municipal WHERE codigo_ibge = '3550308';

SELECT f.url, r.folha, r.linha, r.motivo FROM rejeicoes r
JOIN fontes f ON f.id = r.fonte_id;
```

## Método do índice

1. Usa uma janela comum de 12 meses civis encerrados. Só entram na coorte
   municípios com 12 observações para **cada** crime selecionado e população
   válida. Todas as localidades do cadastro permanecem no CSV; as demais têm
   índice nulo e faixa `indisponivel`.
2. Taxa bruta = ocorrências nos 12 meses / população × 100.000. Densidade =
   população / área em km², guardada apenas como contexto.
3. Suavização empírica Gamma-Poisson: `e_i=pop_i/100000`,
   `mu=sum(N_i)/sum(e_i)`,
   `tau²=max(0,sum((N_i-e_i*mu)²-e_i*mu)/sum(e_i²))`.
   Para `tau²>0`, `beta=mu/tau²`, `alpha=mu*beta`, e taxa suavizada
   `(N_i+alpha)/(e_i+beta)`. Registra a contribuição dos dados `e_i/(e_i+beta)`.
   Quando `tau²=0`, usa a média comum; não cria dispersão artificial.
   É um modelo empírico da coorte, não calibração por sinistros; o prior nacional
   pode reduzir extremos reais e diferenças regionais. Rever sensibilidade antes
   de decisões operacionais.
4. Percentil com empates por posto médio: `100*(posto-1)/(n-1)`.
5. CRITIC sobre esses percentis: `C_j=s_j*sum_k(1-r_jk)`,
   `w_j=C_j/sum(C)`, correlação de Pearson sem módulo. Critérios constantes têm
   peso zero; um único critério variável recebe peso 1. Sem dispersão ou com
   redundância perfeita, o cálculo informa a degeneração e não inventa pesos.
6. Índice = média ponderada dos percentis, entre 0 e 100. Não necessariamente
   ocupa os dois extremos. As faixas 25/50/75 são convenções de comunicação,
   explicitadas no arquivo de configuração, não cortes atuariais aprendidos.

`config/seguranca.json` preserva quatro naturezas de roubo para tornar explícita
a falha de cobertura do recorte original. Os nomes existem no arquivo real,
mas a combinação de granularidade e unidade exigida não existe em 2025.
Não se mistura agregado de roubo com seus subtipos. Confirmar se as definições
da fonte permitem sobreposição entre naturezas. CRITIC estima pesos a partir da
variação e correlação; não demonstra relevância para seguro empresarial, não
corrige subnotificação e não torna a seleção das variáveis uma conclusão objetiva.
O mínimo padrão de 30 municípios é uma salvaguarda operacional declarada, não
um limiar de validade estatística. A coorte observada é explicitada no diagnóstico;
se faltar uma UF, a posição é relativa à cobertura disponível, não a todo o país.

`completude_0_1` é a fração de células crime/mês publicadas na janela. `confianca`
é um rótulo operacional (`insuficiente`, `revisar`, `completo_na_fonte`), com motivos,
defasagem e rejeições visíveis. **Não é intervalo de confiança nem chance de o
dado estar correto.** Não estima o grau de subnotificação.

## Saídas e validação do ranking

`data/seguranca/exportacao/` recebe:

- `indice_municipal.csv`: uma linha por município, código, UF, população/ano,
  área, densidade, índice, faixa, confiança, completude, período e detalhes por crime.
- `cobertura_uf.csv`: municípios cadastrados, completos e pontuados por UF.
- `diagnostico.json`: pesos, parâmetros estimados, alertas, coorte e 30 primeiros
  com contagens, taxas brutas, taxas suavizadas e contribuição da observação.
- `manifesto.json`: configuração, URLs/hashes das entradas e hashes das saídas.

Compare a cobertura por UF; investigue lacunas e linhas rejeitadas. Verifique se
o topo resulta de volumes relevantes, população pequena, mudanças de registro
ou erros de unidade/duplicação. Compare períodos e taxas antes/depois da
suavização. Não ajuste pesos para produzir um ranking visualmente esperado.
A plausibilidade substantiva precisa de revisão humana com os dados reais;
não foi verificada durante o bloqueio de rede.

## Formulário e necessidade de seguro

Em `frontend/`, execute `npm run dev`. O formulário consulta o SQLite pelo
servidor local: `GET /api/seguranca/municipios?uf=SP&q=São%20Paulo` e
`GET /api/seguranca/3550308`. `BB_SEGURANCA_DB` pode indicar outro banco;
`BB_PYTHON` pode indicar o executável do ambiente virtual. As consultas são
somente leitura e parametrizadas; banco ausente retorna 503, código desconhecido
retorna 404 e município sem série retorna índice nulo. Não há fallback de risco baixo.

A mesma execução que gera o CSV grava os índices consultados no SQLite. Assim,
o formulário lê o resultado municipal exportado sem carregar todos os registros
no navegador. Nome completo e UF precisam coincidir; mudar a cidade invalida a
consulta anterior, inclusive respostas ainda em trânsito. Dados pessoais,
endereço completo e valores dos bens não entram na requisição do índice.

Quando existe índice, o formulário pode mostrar posição relativa, período,
qualidade e fontes. O snapshot de 2025 mostra a indisponibilidade. A indicação
de planos por esse contexto foi bloqueada pela falta de validação empresarial.

O cálculo exploratório anterior só é habilitado com validação empresarial
explícita; a API deste contexto retorna `uso_empresarial_validado=false`.
O formulário não pontua bens nem sugere planos usando este recorte. A fórmula
anterior, mantida apenas como hipótese testável no módulo, era:
`(valor_bens/1000)*(indice/100)*f_garagem*f_uso`. Os fatores são **hipóteses de
cenário não calibradas**: garagem fechada 0,85, sem garagem fechada 1,15; uso
interno 1, externo 1,2, misto 1,1. Ficam separados dos pesos CRITIC, versionados em
`frontend/public/security.js` e identificados na interface. Valores desconhecidos
não são presumidos. Pontos não são reais esperados de perda, probabilidade,
prêmio nem recomendação contratual validada. O denominador 1.000 apenas define a
escala dos pontos. A pertinência de garagem/uso ao bem segurado exige revisão.

## Limites substantivos

O índice é relativo entre municípios observados, não probabilidade individual de
ser roubado. O escopo de nove tipos mencionado para o SINESP precisa ser conferido
na edição obtida; o recorte não oferece um indicador de roubo a residência.
Pode haver lacunas por estado, revisões, diferenças de registro e subnotificação.
Não se infere segurança de bairros/ruas a partir de agregados municipais.
Uma probabilidade de sinistro real exigiria dados de sinistros/exposição segurada
ou vitimização e validação externa. Roubo de veículos/carga/bancos não equivale
automaticamente a roubo em estabelecimento empresarial.

## Testes

```bash
"$BB_PYTHON" -m pytest -q
npm --prefix frontend run check
npm --prefix frontend test
```

As verificações com fixtures exercitam importação, zeros versus ausências, conflitos com
rollback, planilhas, junções, suavização, CRITIC, janela comum, cobertura, saída
CSV/SQLite consistente, API e hipóteses do formulário. Esses resultados validam
o software com fixtures. A auditoria real de 2025 está documentada separadamente;
ela identifica as limitações da fonte e não calibra risco atuarial.
