# Demonstração da prospecção passiva por ID de empresa

## Conceito correto

- **CNPJ** é identificador de pessoa jurídica em sistemas reais, sujeito à verificação de titularidade e autorização.
- **CNAE** classifica a atividade econômica e não identifica uma empresa.
- Os CSVs fornecidos no Datathon utilizam `empresa_id` anonimizado, como `EMP_TESTE` ou `EMP_0001` (apenas se houver esse ID de fato nos arquivos).
- Para apresentação do MVP, o visitante digita **o ID de empresa da base**, que simula a localização de um cadastro após identificação bancária. Não existe vínculo CNPJ–ID nos CSVs.

## Uso no Windows

Na pasta do projeto, com os 9 CSVs presentes em `data/desenvolvimento`, dê dois cliques em `Iniciar-Demonstracao-Local.cmd`. Deixe a janela aberta enquanto utiliza a demonstração.

Também é possível iniciar pelo terminal, na pasta do projeto:

```powershell
npm.cmd --prefix frontend run demo:local
```

Abra http://localhost:4176/cotacao e digite um ID **realmente existente na coluna `empresa_id` de `empresas.csv`**, por exemplo `EMP_0001` **apenas se estiver no seu arquivo**.

O iniciador configura `BB_DEMO_ID_LOOKUP=1` somente para esse processo e utiliza a porta **4176** por padrão. Para escolher outra porta, defina `PORT` antes de iniciar. Os comandos comuns `dev` e `start` continuam sem habilitar a demonstração automaticamente. Para encerrar, pressione `Ctrl+C` na janela do servidor.

O sistema consulta o cadastro pelo ID exato; se houver apenas uma unidade, calcula o relatório na hora; se houver mais, pede a escolha da unidade. Nenhuma escolha por CNAE ou lista de empresas é necessária, e nenhuma resposta ausente é inventada. O cliente visualiza os valores e a recomendação preliminar do mesmo `analisar_cadastro` usado internamente, sem ferramenta de ligação.

Para localizar IDs disponíveis no terminal local, sem enviar seus dados:

```powershell
Import-Csv .\data\desenvolvimento\empresas.csv | Select-Object -First 10 empresa_id, descricao_cnae
```

A experiência alternativa de preencher a proposta manualmente continua disponível, sem necessidade de cadastrar um ID.

## Proteção e limites

**Essa rota demonstrativa permanece DESLIGADA por padrão**. O comando `demo:local` habilita explicitamente a demonstração. O servidor rejeita a consulta a menos que `BB_DEMO_ID_LOOKUP=1` e a conexão venha da interface loopback (`127.0.0.1`); a aplicação continua vinculada exclusivamente a `127.0.0.1`. O navegador deve enviar solicitações da mesma origem. Não use `ngrok`, proxy reverso ou redirecionamento para expor a porta do servidor de dados (**4176** na demonstração ou **4174** no início comum).

O relatório usa dados individuais **anonimizados do pacote acadêmico**. Mesmo que sejam anonimizados, podem conter informações comerciais sensíveis. Esse mecanismo é apenas demonstrativo, e **não constitui autenticação ou autorização bancária**. Ele não deve ser utilizado com dados bancários reais ou num domínio público. Em produção, implementar SSO/identidade de cliente e vínculo verificado entre CNPJ, cliente e unidade, além de trilha de auditoria e autorizações por propriedade.

O **ngrok na porta 8765**, quando configurado, serve exclusivamente ao servidor de voz para a Twilio, não deve expor o backend de dados.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend run check
npm.cmd --prefix frontend test
```
