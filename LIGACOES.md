# Ligações com Twilio Voice

O sistema faz uma chamada para o telefone informado e lê uma mensagem em português
com a voz `Polly.Camila`. Depois encerra a chamada. Não é uma conversa por microfone
nem um agente de IA que responde à pessoa. Não faz gravação, discagem em lote ou
chamadas ao abrir a página.

## Configurar e executar

Python 3.12 ou 3.13, na raiz do repositório, no PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:TWILIO_ACCOUNT_SID="AC_SEU_ACCOUNT_SID"
$env:TWILIO_AUTH_TOKEN="SEU_AUTH_TOKEN"
$env:TWILIO_FROM_NUMBER="+SEU_NUMERO_TWILIO"
.\.venv\Scripts\python.exe -m streamlit run ligacao_interface.py --server.address 127.0.0.1
```

Abra o endereço local mostrado pelo Streamlit. Também é possível iniciar `app.py`
e selecionar **Ligações** no menu. Essa seção funciona sem os CSVs do Datathon.
Para executar só a tela de ligações, basta instalar `streamlit>=1.45,<2`.

No Linux/macOS use `.venv/bin/python` e defina variáveis com `export NOME='valor'`.
O arquivo `.env.example` é uma referência; o aplicativo não lê `.env` automaticamente.
As variáveis devem estar no processo que inicia o Streamlit. Não publique o Auth
Token nem coloque credenciais em arquivos versionados. Execute localmente; a tela
não implementa autenticação para uso em um servidor público.

## Preparar a Twilio

1. No console, abra **Communications > Voice > Overview > Try out Voice**.
2. Conclua a configuração gratuita e verifique o telefone de destino.
3. Use em `TWILIO_FROM_NUMBER` o número de teste indicado para aquele destinatário
   e produto. Em conta paga, use um número Twilio ou caller ID autorizado.
4. Copie Account SID e Auth Token para as variáveis de ambiente no seu terminal.
5. Digite o destino no formato E.164: `+`, código do país, DDD e telefone, sem
   espaços ou pontuação. Confira os dados, escreva a mensagem e clique **Ligar agora**.

O teste grátis tem 30 dias, 75 minutos de voz, até cinco destinatários verificados
e chamadas dentro do mesmo país. A origem de teste pode variar por destinatário.
Esses limites e a disponibilidade são controlados pela Twilio. Um upgrade pago
é necessário para destinos fora das restrições do trial; as permissões geográficas
e o saldo da conta continuam se aplicando. Chamadas e síntese de voz podem gerar
cobrança na conta paga. Consulte as tarifas no console antes de usar saldo real.

## Acompanhar e encerrar

Após o envio, a tela mostra o Call SID e o status recebido. **Atualizar status**
consulta a API; **Encerrar chamada** solicita o encerramento. Uma chamada aceita
pode estar na fila, ocupada ou sem atendimento. `completed` pode incluir caixa
postal e não comprova que uma pessoa ouviu a mensagem.

A tela guarda apenas a última chamada na sessão do navegador e bloqueia novos
envios enquanto ela estiver ativa. Não há histórico persistente. Atualize o status
para liberar outra chamada após o encerramento. A proteção é por sessão, não um
limite global entre abas ou usuários.

Se o envio perder a conexão ou retornar erro de servidor, não há repetição
automática: a chamada pode ter sido aceita. Confira **Voice > Logs** no console
antes de clicar em **Já conferi os logs; liberar novo envio**. Se recarregar ou
fechar a sessão, essa proteção local é perdida. A duração é limitada a 120 segundos
por padrão, ajustável entre 10 e 600 segundos; isso não é uma garantia de custo.

## Usar em outro código Python

```python
from ligacoes import ClienteLigacoes, Configuracao

cliente = ClienteLigacoes(Configuracao.do_ambiente())
# Esta linha inicia uma ligação real. Use somente após conferir o destino.
chamada = cliente.ligar(destino, "Olá! Esta é a mensagem do projeto.", limite=120)
print(chamada["sid"], chamada["status"])
print(cliente.consultar(chamada["sid"]))
# cliente.encerrar(chamada["sid"])
```

A integração HTTP usa a biblioteca padrão do Python, com TLS, timeout de 20 segundos,
sem redirecionamentos e sem tentativas automáticas. O TwiML segue no próprio pedido,
sem servidor de webhook ou túnel externo. Texto é escapado como XML e validado
antes do envio. Erros exibidos não incluem o token nem a resposta bruta da Twilio.

## Testar sem ligar

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_ligacoes.py tests/test_ligacao_interface.py -q
```

Os testes substituem o transporte HTTP por respostas simuladas; não precisam de
conta real nem consomem minutos.

## Referências oficiais

- [Teste de Voice e limites](https://www.twilio.com/docs/usage/trials/try-out-voice)
- [API de chamadas](https://www.twilio.com/docs/voice/api/call-resource)
- [Síntese de voz](https://www.twilio.com/docs/voice/twiml/say)
- [Voz brasileira Polly.Camila](https://www.twilio.com/en-us/changelog/end-support-alice-text-to-speech-voice-2023)
