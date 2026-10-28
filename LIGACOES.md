# Ligações com Twilio Voice

## Teste grátis (padrão)

Para experimentar uma fala própria em português sem TwiML Bin, veja
[VOZ_PERSONALIZADA.md](VOZ_PERSONALIZADA.md). Essa opção requer um servidor e
uma URL HTTPS externa, e depende das permissões de Custom da conta Twilio.

Sem `TWILIO_TWIML_URL`, o modo `trial` chama um destino verificado e reproduz o
template de demonstração Text-to-Speech da Twilio. Com essa variável, o app usa
o roteiro servido pela URL HTTPS indicada. Para editar a fala no servidor deste
projeto, altere `mensagem_ligacao.txt`, conforme o guia de voz personalizada.
O número de origem de teste é atribuído pela Twilio.

No PowerShell, na raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:TWILIO_ACCOUNT_SID="AC_SEU_ACCOUNT_SID"
$env:TWILIO_AUTH_TOKEN="SEU_AUTH_TOKEN"
$env:TWILIO_MODE="trial"
.\.venv\Scripts\python.exe -m streamlit run ligacao_interface.py --server.address 127.0.0.1
```

Se o ambiente já existe e as dependências estão instaladas, não repita a criação.
Se o aplicativo está rodando, pressione Ctrl+C e inicie novamente no mesmo terminal.
O modo padrão, sem TWILIO_MODE, é trial. TWILIO_FROM_NUMBER não é enviado no trial.
No Linux/macOS, use `.venv/bin/python` e defina as variáveis com `export`.
O arquivo `.env.example` é uma referência: o app não lê `.env` automaticamente.

No console, abra **Communications > Voice > Overview > Try out Voice** e conclua
a verificação do telefone de destino. Use esse telefone com `+`, país, DDD e número,
sem espaços. A conta de teste permite até cinco destinatários verificados no mesmo
país, tem 75 minutos e expira em 30 dias. A Twilio impõe os limites de duração e uso.

O pedido de criação no trial contém apenas `To` e `Url`. Sem URL própria,
usa o template oficial:
`https://webhooks.twilio.com/v1/Voice/Template/voice_text_to_speech`.
Não envia `From`, `Twiml`, `TimeLimit` nem `Timeout`, pois a API de teste limita os
parâmetros. Não há repetição automática com parâmetros diferentes. O fluxo com
URL própria depende da permissão de Custom na conta Twilio.

## Mensagem personalizada em português (modo completo)

Use este modo somente se sua conta já foi habilitada pela Twilio para os recursos
completos. Selecionar o modo não faz upgrade da conta. Chamadas e síntese de voz
podem consumir saldo conforme as tarifas da conta.

```powershell
$env:TWILIO_MODE="completo"
$env:TWILIO_FROM_NUMBER="+SEU_NUMERO_AUTORIZADO_TWILIO"
.\.venv\Scripts\python.exe -m streamlit run ligacao_interface.py --server.address 127.0.0.1
```

Mantenha Account SID e Auth Token definidos nesse terminal. A tela mostrará os
campos de mensagem e duração. O texto é lido em português com `Polly.Camila`,
e a chamada termina após a mensagem. O limite padrão é 120 segundos, ajustável
entre 10 e 600 segundos. Isso não é garantia de custo. O sistema não é uma conversa
por microfone ou agente de IA; não grava nem faz discagem em lote.

## Acompanhar e encerrar

A última chamada fica na sessão do navegador com Call SID, status, consulta e
pedido de encerramento pela API. O suporte a operações depende das permissões da
conta. Uma chamada aceita pode terminar ocupada ou sem atendimento; `completed`
também pode incluir caixa postal e não comprova que uma pessoa ouviu a mensagem.

A sessão bloqueia outro envio enquanto a última chamada estiver ativa. Atualize o
status após o encerramento. Não existe histórico persistente ou limite global
entre abas. Se o pedido perder a conexão ou houver erro de servidor, confira os
logs de Voice antes de liberar outro envio: a chamada pode ter sido aceita. Fechar
ou recarregar a sessão perde essa proteção local.

## Usar em Python

```python
from ligacoes import ClienteLigacoes, Configuracao
cliente = ClienteLigacoes(Configuracao.do_ambiente())
# Inicia uma chamada real; use somente com o destino conferido e autorizado.
chamada = cliente.ligar(destino)  # modo trial
# No modo completo: cliente.ligar(destino, "Olá, esta é nossa mensagem.", limite=120)
print(cliente.consultar(chamada["sid"]))
# cliente.encerrar(chamada["sid"])
```

O transporte usa HTTPS, timeout HTTP de 20 segundos, sem redirecionamentos e sem
repetições automáticas. O modo completo envia TwiML escapado como XML, sem precisar
de webhook próprio. Erros desconhecidos incluem a explicação do provedor com
credenciais e telefones ocultos. Não publique tokens em arquivos versionados.
Execute localmente: a tela não implementa autenticação para acesso público.
A opção **Ligações** em `app.py` também funciona sem os CSVs do Datathon.

## Testes sem ligações reais

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Os testes simulam a API e não consomem minutos. Cobrem o pedido mínimo do trial,
texto escapado e limites no modo completo, erros e os dois fluxos de interface.
Uma chamada real deve ser validada pelo usuário com seu destino verificado.

## Referências oficiais

- [Parâmetros e restrições do trial](https://www.twilio.com/docs/usage/trials/try-out-voice)
- [API completa de chamadas](https://www.twilio.com/docs/voice/api/call-resource)
- [Síntese de voz](https://www.twilio.com/docs/voice/twiml/say)
