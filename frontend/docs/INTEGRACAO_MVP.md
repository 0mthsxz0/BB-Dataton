# Formulário integrado ao MVP

Implementação de 28/10/2026 na branch `codex/formulario-cotacao-busca-inteligente`.

## Como os itens 3 e 4 funcionam

O item 3 reaproveita `processamento.agregar_bens`: cada bem contribui com `valor_cadastrado × probabilidade_bem_no_imovel_referencia`, uma única vez. O vínculo empresa/unidade é validado. Equipamentos são uma parcela do total dos bens; não são somados novamente. O estoque entra separadamente, sem adicionar estoque médio e pico no mesmo cenário. O formulário pode confirmar os valores de reposição: um valor preenchido substitui o agregado cadastrado, zero confirma ausência e vazio preserva o cadastro. Sem cadastro, vazio permanece desconhecido. Reconstrução, quando informada, exclui o terreno e entra no cenário patrimonial, não no roubo de conteúdo.

As fontes públicas entram por código municipal ou classe CNAE. Para nova cidade, o adaptador consulta a [API de localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades), enviando somente a UF e comparando o nome da cidade. Uma unidade vinculada pode usar o código municipal já cadastrado. Se a API falhar, é permitido resolver nome e UF exatos nos snapshots públicos distribuídos. Sem correspondência, os indicadores territoriais permanecem desconhecidos.

O item 4 executa o mesmo motor Python do MVP, com quatro índices de prioridade e seis heurísticas das coberturas comuns. A fórmula continua:

```text
P = 100 × clip[(0,25 + 0,75 I) × (0,20 + 0,80 R) × (0,70 + 0,30 V)
               + k × I × R × D, 0, 1]
```

`R` é exposição relativa ao evento, `I` é impacto e `V` é vulnerabilidade. A normalização financeira é logarítmica. Valores maiores de bens afetam impacto, sem aumentar automaticamente a exposição territorial. Pisos, pesos e interações são hipóteses experimentais; a nota não é probabilidade de sinistro nem taxa atuarial.

## Oito perguntas obrigatórias

O texto e os IDs estão em `public/questionnaire.json`, consumido por frontend e backend.

| Índice | Perguntas Sim/Não | Uso |
| --- | --- | --- |
| Roubo/furto/arrombamento | Há alarme monitorado e controle de acesso funcionando? Há bens de fácil transporte e revenda? | `R = 0,70 território + 0,15 ausência de controles + 0,15 bens transportáveis` |
| Vendaval | Telhado e fixações foram inspecionados e estão em bom estado? Há bens ou estruturas externas expostas? | `V = 0,50 vulnerabilidade MVP + 0,25 ausência de manutenção + 0,25 exposição externa` |
| RC empregador | Há empregados na unidade? Eles executam tarefas com exposição física? | Sem empregados: zero. Caso contrário, `R = 0,70 NR-4 + 0,30 tarefas com exposição` |
| Vidros | Há vidros/espelhos/vitrines a proteger? Estão expostos à rua, circulação ou impactos? | Sem vidros: zero. Caso contrário, fator de presença `0,60 + 0,40 exposição`, combinado com o fator de atividade do MVP |

Respostas não vêm pré-selecionadas. Tipos precisam ser booleanos na API; strings como `"false"` são rejeitadas. Contradições entre ausência, exposição, quantidade e valores são recusadas. Declarações têm confiança limitada, sem equivaler a vistoria.

Para grupos comuns há um mapa editorial dos códigos da seguradora para os grupos contextuais já existentes no MVP. Fora desse mapa, o fator fica desconhecido. CNAE é separado: vem do cadastro ou é informado explicitamente. A busca nunca inventa um CNAE para um código do catálogo da seguradora. O CNAE herdado precisa ser conferido ao trocar a atividade.

## Recomendação de plano

Ao selecionar uma empresa/unidade em “Usar cadastro existente do Datathon”, o formulário chama `POST /api/recomendacao/cadastro` e mostra imediatamente uma análise inicial na mesma etapa. Essa análise executa o motor original do MVP sobre o registro da unidade e as referências já disponíveis. Não exige atividade do catálogo nem respostas de questionário, não presume respostas e não modifica o cadastro. A interface exibe o patrimônio, valores observados, memória dos quatro índices, as dez necessidades com seus pesos e a comparação de pontos/aderência dos três planos. A conclusão inclui incerteza e pendências. Uma seleção nova descarta o resultado anterior; respostas atrasadas de consultas anteriores não substituem a unidade atual. Erros permitem nova tentativa.

A indicação inicial fica identificada como análise do cadastro; a análise posterior do formulário continua incluindo as oito respostas e as alterações declaradas. Os dois resultados têm contextos explícitos e podem indicar planos diferentes.

`recomendador.recomendar_plano` compara as dez necessidades ponderadas e recomenda o menor plano que alcança a meta configurada, atualmente 80%, e inclui as coberturas indispensáveis. A interface exibe a aderência dos três planos, lacunas prioritárias, confiança, sensibilidade, fontes e pendências. É possível escolher outro plano. Preços continuam referências públicas; prêmio e aceitação não são calculados pelo MVP.

Alterar cadastro, atividade, endereço, escopo, valores ou respostas invalida o resultado anterior e bloqueia o avanço para planos até recalcular. Alterar somente contato ou preferência de pagamento preserva a análise.

## Dados públicos e SSP

O projeto já distribui segurança contextual IBGE/PNAD de 2021 para 27 capitais, clima histórico ERA5/Open-Meteo para dez municípios e referência contextual CNAE/NR-4 de 2023. Os períodos e fontes são exibidos. A presença de um snapshot não significa dados atuais ou cobertura geográfica nacional. Sem informação: ponto neutro explícito, confiança menor e faixa de sensibilidade ampla.

A [SSP-DF publica XLS e PDF por região e período](https://www.ssp.df.gov.br/dados-por-regiao-administrativa/). A implementação usa o importador validado do MVP, não presume uma API nacional homogênea. Para integrar arquivos oficiais obtidos dessas fontes:

```powershell
.\.venv\Scripts\python.exe scripts/importar_ssp.py --manifesto examples/manifesto_ssp.csv --saida data/referencias/seguranca_ssp.csv
```

Crie a pasta de saída se necessário e preencha o manifesto com arquivos efetivamente disponíveis, fonte, ano e código IBGE. A referência SSP documentada passa a substituir a proxy de segurança nos municípios cobertos. Uma única cidade sem contraste recebe confiança zero. Não atribuímos uma região administrativa a partir de CEP ou coordenadas perturbadas. Segurança e clima carregam metodologias diferentes; não são multiplicados indiscriminadamente em todas as coberturas.

## APIs locais

| Rota | Contrato |
| --- | --- |
| `GET /api/contexto` | Lista apenas IDs, cidade/UF e grupo dos estabelecimentos da base local, sem contatos |
| `POST /api/atividades/buscar` | `{description}` → até três sugestões reais com razões, confiança de correspondência e subatividade vinculada, quando inequívoca |
| `POST /api/recomendacao` | IDs do catálogo, vínculo opcional, cidade/UF, escopo, valores opcionais, CNAE e oito respostas → índices, dimensionamento, patrimônio, fontes e comparação dos planos |
| `POST /api/recomendacao/cadastro` | `{empresaId, imovelId}` → recomendação inicial pelo cadastro, quatro índices, dados utilizados, necessidades e memória de comparação; `respostas: null` |

Node executa o adaptador Python por stdin, sem shell e sem criar arquivos de proposta. O processo é limitado a 30 segundos e a quatro análises simultâneas. POST exige JSON, origem local e corpo limitado. Falha no Python gera erro visível e permite tentar novamente; nunca produz plano fictício de contingência.

Contatos, nascimento, CNPJ, endereço completo, CEP e dados de pagamento não entram no payload de recomendação. Não há envio à seguradora ou a uma IA externa. O servidor escuta somente em `127.0.0.1`. Autenticação e integração com sistemas reais do BB exigiriam um backend de produção autorizado; não são representadas pela seleção da base local.

## Busca inteligente sem API generativa

A API local usa normalização, pesos por raridade dos termos, conceitos/sinônimos, prefixos, trigramas, diferenciação de fabricação/varejo/atacado/reparação e palavras das subatividades. Retorna somente os 970 IDs reais e seus 1.007 vínculos do snapshot. A seleção depende de confirmação. Linguagem vaga pede detalhe; empates de subatividade exigem escolha. É recuperação textual com regras, sem promessa de compreensão irrestrita de linguagem natural.

Expansões editoriais, inclusive `frigorif → frigorífico`, ocorrem no gerador `scripts/preparar_catalogo_cotacao.py`. As fontes congeladas e os identificadores originais são preservados. Para regenerar o catálogo:

```powershell
.\.venv\Scripts\python.exe scripts/preparar_catalogo_cotacao.py
```

## Validação

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend run check
npm.cmd --prefix frontend test
```

A suíte inclui monotonicidade de cada resposta, exclusões por ausência de empregados/vidros, escopo, patrimônio sem dupla ponderação, precedência cadastro/formulário, dez necessidades, relações válidas do catálogo, entradas inválidas, indisponibilidade do IBGE e exclusão de dados pessoais do payload. O fluxo completo também foi percorrido no navegador com valores fictícios.


Atualização do item 10: veja [GUIA_ATUALIZADO.md](GUIA_ATUALIZADO.md). Matriz do desafio 6/8/10, cobertura cibernética obrigatória, triagem e composição personalizada implementadas na versão 0.4.
