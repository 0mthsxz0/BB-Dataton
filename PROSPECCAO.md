# Da recomendação à ligação com roteiro personalizado

O protótipo agora permite editar a mensagem na própria interface Streamlit, inclusive
no modo trial com URL HTTPS própria. O relatório alimenta um modelo de texto com
variáveis; o colaborador revisa o resultado antes de iniciar uma chamada.

## Usar somente a tela de ligações

Mantenha `servidor_voz.py` e `ngrok http 8765` ligados, conforme o guia
[VOZ_PERSONALIZADA.md](VOZ_PERSONALIZADA.md). Se o servidor foi iniciado antes desta
atualização, reinicie-o: a nova versão também atende os roteiros individuais.

No PowerShell que iniciará o Streamlit:

```powershell
$env:TWILIO_ACCOUNT_SID="AC_SEU_ACCOUNT_SID"
$env:TWILIO_AUTH_TOKEN="SEU_AUTH_TOKEN"
$env:TWILIO_MODE="trial"
$env:TWILIO_TWIML_URL="https://SEU-DOMINIO.ngrok-free.dev/voz.xml"
.\.venv\Scripts\python.exe -m streamlit run ligacao_interface.py --server.address 127.0.0.1
```

Na página, escreva ou edite **Mensagem que será falada**. Confira o telefone e o
texto, marque a confirmação e clique em **Ligar agora**. Não é necessário editar o
arquivo TXT para cada ligação. A mensagem inicial vem de `mensagem_ligacao.txt`,
mas o envio usa o texto que foi revisado no campo da tela.

## Usar a análise da empresa como origem

No mesmo terminal configurado, inicie o aplicativo principal em vez do aplicativo
isolado:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

1. Configure a pasta dos CSVs na barra lateral, ou pela variável BB_DATATHON_DADOS,
   conforme [README.md](README.md). Não são criados dados reais automaticamente.
2. Em **Analisar estabelecimento**, escolha a unidade da empresa.
3. Revise o plano sugerido, prioridades, fatores, confiança, comparação e pendências.
4. Se desejar, clique em **Baixar relatório desta análise** para obter o JSON
   completo daquele estabelecimento, com registro, pontuações e recomendação.
5. Ao final da análise, clique em **Preparar ligação com esta recomendação**.
6. A seção **Ligações** abre com o contexto da empresa e da unidade selecionadas.
7. Confirme o nome comercial, pois a base pode trazer apenas um identificador.
8. Preencha nome do contato, nome do colaborador e equipe/organização, se aplicável.
9. Clique em **Gerar mensagem do relatório**. Se alterar esses campos ou o modelo,
   clique novamente para atualizar o rascunho.
10. Edite o campo **Mensagem que será falada** para fazer a revisão final.
11. Informe o telefone de destino e confirme antes de clicar em **Ligar agora**.

Nome e telefone do contato não são inferidos de colunas de atividade, CNPJ ou
endereço. O telefone é informado pelo colaborador e, no trial, deve estar verificado.
Não há disparo automático ao abrir ou recalcular uma recomendação.

## Modelo base e variáveis

Abra **Editar o modelo com variáveis** para alterar o roteiro. Um exemplo curto:

```text
{saudacao} {apresentacao} Gostaria de conversar sobre a proteção da empresa
{empresa}. A análise preliminar sugeriu o plano {plano}. {argumento}
{ressalvas} Podemos agendar uma conversa?
```

| Variável | Origem |
| --- | --- |
| `{saudacao}` | Nome do contato informado, ou saudação genérica |
| `{apresentacao}` | Colaborador e organização informados |
| `{empresa}` | Nome revisado na tela; inicialmente razão social, fantasia ou ID disponível |
| `{atividade}` | Descrição CNAE ou grupo de atividade do registro |
| `{cidade}` | Município da unidade |
| `{plano}` | Plano produzido por recomendar_plano |
| `{coberturas_prioritarias}` | Até duas prioridades entre as coberturas do plano sugerido |
| `{argumento}` | Frase baseada nessas prioridades |
| `{justificativa}` | Justificativa interna da recomendação, disponível para uso opcional |
| `{ressalvas}` | Validação dos dados, cotação, contratação e incertezas relevantes |

As variáveis são preenchidas por regras em `mensagens_prospeccao.py`. Não há
chamada a um modelo de IA externo nem texto inventado a partir de dados ausentes.
A seleção de prioridades exclui proteções adicionais que não fazem parte do plano.
As notas não são probabilidades de sinistro. O modelo padrão preserva a natureza
preliminar da recomendação e não inclui faturamento, valores de bens ou todo o
relatório na fala. Qualquer alteração manual do roteiro precisa ser revisada.

O modelo aceita somente nomes de variáveis listados, sem execução de expressões.
O texto preenchido precisa caber nos limites de mensagem/XML da aplicação. Em
**Conferir dados usados na mensagem**, veja os valores usados e as prioridades.

## Roteiro exclusivo de cada envio

O texto do campo é validado e salvo antes de solicitar a chamada. O sistema gera
um identificador aleatório de 256 bits e entrega o roteiro em uma rota como:

```text
https://SEU-DOMINIO.ngrok-free.dev/voz/IDENTIFICADOR_ALEATORIO.xml
```

O pedido à Twilio usa essa URL exclusiva. Editar o rascunho depois não altera uma
chamada já enviada. Duas chamadas guardam textos separados. O relatório completo
e o telefone não são colocados na URL. O arquivo TXT compartilhado continua sendo
usado apenas na rota de demonstração `/voz.xml` e como texto inicial da tela.

Os roteiros são guardados em `tmp/roteiros_voz/`, excluído do Git. O acesso expira
após uma hora e retorna HTTP 410. Arquivos antigos são removidos na próxima criação
de roteiro; se não houver novas criações, podem permanecer no disco sem serem
servidos. Um pedido recusado pela Twilio também pode deixar um roteiro até expirar.

A interface e o servidor precisam usar a mesma pasta do projeto. Para configurar
outro diretório, defina `BB_ROTEIROS_DIR` com o mesmo caminho nos dois processos.
Em implantação com máquinas diferentes, essa persistência local deve ser
substituída por armazenamento compartilhado e protegido.

## Limites para o futuro painel interno

O fluxo está implementado no protótipo; ainda não é uma implantação de produção.
O painel atual não tem autenticação de colaboradores, integração com CRM,
permissões por equipe, registro persistente de consentimento ou auditoria de
chamadas por usuário. A proteção contra reenvio é por sessão do Streamlit.

O endpoint XML não valida a assinatura da Twilio. A URL aleatória funciona como
um endereço de acesso ao roteiro por tempo limitado; quem a obtiver poderá ler a
mensagem nesse período. Não coloque dados confidenciais em demonstrações. Antes
de usar dados de clientes em produção, implemente autenticação no painel,
controle de acesso e retenção do armazenamento, validação dos webhooks, auditoria
e confirmação das condições comerciais e operacionais do produto.

O relatório e o roteiro não fazem uma oferta vinculante nem confirmam aceitação
contratual. A interface continua apresentando os limites do motor e os dados
pendentes. A fala é um roteiro de apresentação, não uma conversa de IA em tempo real.

## Arquivos principais

| Arquivo | Responsabilidade |
| --- | --- |
| `app.py` | Análise, relatório individual e passagem do contexto para ligação |
| `mensagens_prospeccao.py` | Variáveis, modelo base e preenchimento validado |
| `ligacao_interface.py` | Geração, edição, revisão e solicitação da chamada |
| `roteiros_voz.py` | Persistência e validade dos textos individuais |
| `servidor_voz.py` | Entrega das rotas XML |
| `ligacoes.py` | Transporte HTTP para Twilio, validações e voz pt-BR |

Testes sem chamadas reais:

```powershell
.\.venv\Scripts\python.exe -m pytest tests test_motor.py test_dados_exportacao.py -q
```

São verificados preenchimento a partir do relatório, seleção das coberturas,
troca de contexto, edição na tela, fluxo de navegação, textos independentes,
expiração e envio dos parâmetros de trial. A chamada real com sua conta e seu
destinatário ainda precisa ser confirmada pelo operador.
