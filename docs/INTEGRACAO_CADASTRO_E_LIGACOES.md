# Integração do cadastro verificado e ligações com IA — BB-Dataton

## Implementação

Branch `feature/ligacoes-ia-painel`, baseada na `main`.

O site público `/cotacao` permite identificar uma pessoa jurídica com CNPJ e código de vínculo validado no servidor. O sistema executa a recomendação inicial com os dados **já disponíveis**, pré-preenche informações e mantém como perguntas apenas as informações que precisam de confirmação. Se todos os campos indispensáveis estiverem confirmados, segue diretamente ao resultado; a ausência de resposta nunca é interpretada como "não".

O painel `/interno` tem autenticação local de demonstração, exibe o relatório da unidade e inclui geração de roteiro, edição, aprovação e chamada individual. Os componentes de Twilio/TTS foram portados da branch `codigo-ligacao`. A análise é calculada no servidor com o vínculo selecionado; um relatório arbitrário enviado pelo navegador não é aceito como fonte do roteiro.

A geração de texto utiliza `OPENAI_API_KEY` quando configurada, com conjunto restrito de fatos. Sem a chave, usa roteiro determinístico, sem inventar dados. Nos dois casos, exige revisão e aprovação humana. **É telefonia com roteiro por voz sintética (TTS), não conversa bidirecional de IA.**

## Executar no Windows

Requisitos: Python 3.12/3.13, Node 20+ e, para consultar registros, CSVs do Datathon acessíveis localmente.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:BB_INTERNAL_PASSWORD="ESCOLHA_SENHA_FORTE_COM_12_CARACTERES_OU_MAIS"
npm.cmd --prefix frontend run dev
~~~

Abra http://localhost:4174/interno (colaborador) ou http://localhost:4174/cotacao (cliente).

## Cadastro por CNPJ — configuração necessária

**O pacote acadêmico é anonimizado: não contém CNPJ real.** Seus identificadores de empresas e imóveis não são CNPJ, e **CNAE não identifica uma empresa**. Para recuperar dados por CNPJ é preciso um vínculo externo validado e autorizado. Configure um arquivo privado, fora do Git, no seguinte formato:

~~~json
[
  {
    "cnpj": "CNPJ_VALIDO_DA_EMPRESA",
    "empresaId": "IDENTIFICADOR_DO_CSV",
    "imovelId": "IDENTIFICADOR_DA_UNIDADE",
    "codeSha256": "HASH_SHA256_HEXADECIMAL_DO_CODIGO_PRIVADO"
  }
]
~~~

O código privado deve possuir pelo menos oito caracteres; `codeSha256` contém o seu SHA-256 hexadecimal, não o segredo em texto claro. No servidor:

~~~powershell
$env:BB_CLIENT_MAP_FILE="C:\CAMINHO_PRIVADO\vinculos.json"
~~~

A verificação consulta somente esse arquivo no backend. Não retorna informações privadas a visitantes não verificados e não aceita selecionar outra empresa por IDs fornecidos pelo navegador. Em produção, esse vínculo demonstrativo deve ser substituído por identidade bancária (SSO/MFA e autorização de cliente/unidade).

## Como usar o módulo de voz

1. Entre em `/interno` e selecione uma empresa/unidade da base.
2. Consulte o relatório inicial ou conclua as perguntas e calcule uma análise refinada.
3. Na seção **Ligar a partir deste relatório**, clique em **Gerar roteiro do relatório**.
4. Edite a fala, confira seu conteúdo e clique em **Aprovar este texto**.
5. Informe um telefone E.164 (exemplo: `+5561999999999`), confirme a autorização comercial e a decisão de ligar e clique em **Ligar agora**.
6. O status inicial da solicitação é exibido; erros de rede exigem consulta aos registros antes de qualquer nova tentativa.

**Chamadas reais estão desligadas por padrão.** Para homologar, configure credenciais válidas da Twilio e habilite o envio explicitamente:

~~~powershell
$env:BB_VOICE_ENABLED="1"
$env:TWILIO_ACCOUNT_SID="AC...SUA_CONTA"
$env:TWILIO_AUTH_TOKEN="SEU_TOKEN_PRIVADO"
$env:TWILIO_MODE="completo"
$env:TWILIO_FROM_NUMBER="+55NUMERO_AUTORIZADO"
# Opcional: $env:OPENAI_API_KEY="CHAVE_PRIVADA"
# Opcional: $env:BB_VOICE_MODEL="gpt-4.1-mini"
~~~

O modo completo fornece TwiML diretamente à Twilio. Para o modo `trial`, configure o servidor separado `servidor_voz.py` atrás de túnel HTTPS público, no mesmo armazenamento de roteiros, e `TWILIO_TWIML_URL=https://.../voz.xml`; o destino precisa estar verificado na conta trial.

**Nenhuma ligação real é realizada nos testes.**

## Segurança e limitações

- A aplicação continua ouvindo apenas `127.0.0.1`. O login interno e o arquivo de vínculo são recursos **exclusivamente de demonstração**, não autenticação bancária de produção.
- Sessões locais usam cookie HTTP-only, SameSite Strict e expiração; sem autenticação o visitante público não pode consultar o cadastro, a lista de empresas ou disparar chamadas.
- O roteiro inclui apenas resumo de atividade, município, plano preliminar e prioridades justificadas, não o inventário integral ou dados pessoais. O contato é informado pelo operador e não enviado ao serviço de IA.
- Roteiros exigem aprovação específica e expiram; chamadas já solicitadas não são repetidas automaticamente, mesmo com status incerto.
- Para produção são indispensáveis SSO, perfis por colaborador, autorização por empresa, rate limiting, registro persistente e auditável de consentimento, relatórios e telefonia, políticas LGPD, autenticação de webhooks, tratamento de chamadas e prevenção de abuso.
- Não existe cotação oficial nem cálculo de preço, aceitação contratual ou agente de voz bidirecional.
- O uso de IA externa deve passar pela avaliação de privacidade e contratos de tratamento de dados antes de incluir informações reais de clientes.

## Testes

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend run check
npm.cmd --prefix frontend test
~~~

Os testes automatizados usam dados sintéticos, validam controles de acesso, condições de aprovação e o adaptador Twilio sem realizar chamadas.

## Desenvolvimento posterior

Integrar identidade bancária real e a base operacional, adicionar controle de vínculo para cada unidade/estabelecimento, auditoria persistente e status Twilio via webhooks verificados. Agente de IA conversacional em tempo real requer um projeto específico, separado da leitura de texto TTS.
