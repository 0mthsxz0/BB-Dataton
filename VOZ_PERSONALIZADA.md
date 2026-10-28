# Fala em português sem TwiML Bin

O TwiML Bin está bloqueado nesta conta trial. O caminho alternativo é fornecer
uma URL HTTPS de um servidor próprio na opção Custom. A disponibilidade de
Custom na sua conta deve ser confirmada com uma chamada de teste: os testes
automatizados deste código não verificam as permissões da conta Twilio.

## 1. Editar a fala

Abra `mensagem_ligacao.txt` na raiz do projeto e escreva seu roteiro em português.
Salve como UTF-8. São aceitos até 1500 caracteres, sujeito ao limite XML escapado.
O servidor relê esse arquivo em cada solicitação. O idioma e a voz são definidos
por `criar_twiml()` em `ligacoes.py`: pt-BR e Polly.Camila.

## 2. Iniciar o servidor local

No PowerShell, na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe servidor_voz.py
```

O endereço local é `http://127.0.0.1:8765/voz.xml`. Ele entrega apenas o XML de
fala, não lista pastas, não inicia chamadas nem lê credenciais. GET e POST são
aceitos, pois a Twilio pode buscar o roteiro com ambos os métodos.

## 3. Criar o endereço HTTPS temporário

É necessário ter `cloudflared`, obtido da fonte oficial, instalado ou baixado.
Este projeto não instala nem inicia túneis automaticamente. Em outro terminal:

```powershell
cloudflared tunnel --url http://127.0.0.1:8765
```

A ferramenta mostra uma URL como `https://nome-aleatorio.trycloudflare.com`.
Acrescente `/voz.xml`. Quem tiver essa URL poderá ler o roteiro. Não coloque
informações privadas no texto. O túnel é temporário e destinado a desenvolvimento;
ele deve ficar ligado durante o teste. Pare-o com Ctrl+C quando terminar.
Não aponte o túnel para a porta 8501 do Streamlit.

## 4. Configurar a chamada

Cole o endereço HTTPS completo no campo **Custom TwiML URL** da Twilio. Confira
o destino verificado antes de iniciar a chamada. Para usar o mesmo roteiro no
programa Python, mantenha Account SID e Auth Token no seu PowerShell e defina:

```powershell
$env:TWILIO_MODE="trial"
$env:TWILIO_TWIML_URL="https://nome-aleatorio.trycloudflare.com/voz.xml"
.\.venv\Scripts\python.exe -m streamlit run ligacao_interface.py --server.address 127.0.0.1
```

O endereço muda quando o túnel é reiniciado. Atualize a variável, reinicie o app
e atualize o campo Custom na Twilio. Sem TWILIO_TWIML_URL, o app continua usando
a demonstração padrão da Twilio. Não há upgrade automático nem garantia de que
a conta permita uma URL externa; se o provedor recusar, a tela mostra o erro.

Referências:
- https://www.twilio.com/docs/usage/trials/try-out-voice
- https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
