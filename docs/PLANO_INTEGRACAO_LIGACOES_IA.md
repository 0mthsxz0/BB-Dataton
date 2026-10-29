# Plano de integração — ligações com IA a partir do relatório interno

**Projeto:** Protege Empresa / BB-Dataton  
**Alvo:** `main`, após a promoção do produto v0.4  
**Origem a aproveitar:** `codigo-ligacao`  
**Status:** planejamento técnico; **a integração descrita neste arquivo ainda não foi implementada**.

## 1. Objetivo

Após o cálculo e a geração de um relatório para uma empresa/estabelecimento, disponibilizar no **painel interno do colaborador** a opção **Preparar ligação com IA**.

A IA deverá gerar um **rascunho personalizado de abordagem comercial** exclusivamente a partir de fatos rastreáveis e autorizados do relatório. O colaborador revisa, edita, aprova e decide se deseja iniciar uma ligação individual. A chamada usa uma voz sintética identificada como tal e o texto aprovado. O MVP será uma ligação **unidirecional, com leitura de mensagem (TTS)**. Atendimento conversacional bidirecional por IA é uma fase posterior e **não faz parte da integração inicial**.

## 2. Estado atual — evidências do código

- `main` contém o motor de recomendação, formulário e API local Node.js -> Python.
- O caminho `/interno` presente em `frontend/server.mjs` atualmente aponta para `quote.html`; **não existe ainda um painel interno autenticado e separado**.
- A branch `codigo-ligacao` deriva de `DevC`, uma base **diferente** da aplicação consolidada. **Não fazer merge direto sem integração seletiva.**
- `ligacoes.py` já integra a API Twilio Voice, valida números E.164, oferece consulta e encerramento de chamadas, possui tratamento de erros e TwiML TTS (`Polly.Camila`).
- `mensagens_prospeccao.py` já cria roteiros determinísticos a partir da recomendação. **Não utiliza LLM nem produz conversas de IA**.
- `roteiros_voz.py` cria um roteiro por chamada com identificador não previsível e validade temporária; `servidor_voz.py` serve o TwiML. A implantação demonstrativa usa URL HTTPS/ngrok.
- `PROSPECCAO.md`, `LIGACOES.md` e `VOZ_PERSONALIZADA.md` documentam o protótipo e suas restrições. Atualmente não há CRM, autenticação de colaboradores, persistência de consentimento, fila de trabalho ou integração com painel web.

## 3. Jornada do colaborador

1. Abrir o **painel interno** (acesso autenticado e autorizado) e selecionar a empresa/unidade.
2. Solicitar ou consultar a recomendação existente; salvar um **snapshot versionado do relatório**, com identificador e hash.
3. Conferir plano sugerido, coberturas efetivamente contempladas, prioridades, proveniência, restrições e informações faltantes.
4. Clicar em **Preparar ligação com IA**. Esta ação **não efetua ligação**.
5. Gerar um roteiro a partir de um objeto controlado do relatório, por exemplo: nome comercial confirmado, setor, município, plano preliminar, até duas prioridades verificadas e ressalvas.
6. Exibir a prévia com **texto editável**, indicação de conteúdo gerado por IA, fatos de origem, avisos de ausência de dados e informação de que não é cotação vinculante.
7. O colaborador informa ou confirma destinatário, telefone, finalidade, base legítima/consentimento aplicável e permissões de contato. A interface não infere telefone ou titularidade dos CSVs.
8. O colaborador aprova explicitamente o texto e clica em **Ligar agora**; o backend valida novamente os dados e cria **uma única** solicitação de chamada.
9. Mostrar estado da Twilio e resultado conhecido (solicitada, em andamento, concluída, ocupada, não atendida, falha ou indeterminado), sem presumir que o cliente ouviu a mensagem.
10. Registrar tentativa, colaborador responsável, versão do roteiro aprovado e resultado; permitir novo contato somente por ação consciente, com prevenção de duplicidade.

## 4. Arquitetura de referência

```text
[Relatório do motor + evidências]
             |
             v
[Snapshot de relatório interno/versionado]
             |
             v
[Painel do colaborador /interno]
             |
             v
[Backend autenticado: preparar roteiro]
             |
             +--> [Normalizador + allowlist de fatos]
             |            |
             |            v
             |     [Gerador de texto IA]
             |            |
             |            v
             |     [Validador de fatos e políticas]
             |            |
             +<-----------+
             |
             v
[Rascunho editável + aprovação humana]
             |
             v
[Autorização e verificação de contato]
             |
             v
[Adaptador Twilio + TwiML de uso único]
             |
             v
[Estado da chamada + auditoria]
```

Módulos recomendados:

- `frontend/public/interno.html`, `interno.js`, `interno.css`: tela interna específica, sem reutilizar `quote.html`.
- `painel/relatorios.py`: snapshot e projeção segura do relatório.
- `prospeccao/contexto.py`: contrato com fatos permitidos, proveniência, pendências e normalização.
- `prospeccao/gerador_ia.py`: adaptador de provedor de LLM configurável no servidor, retorno estruturado e fallback determinístico.
- `prospeccao/validacao.py`: validação de conformidade e fatos suportados (não aceitar argumentos sem lastro).
- `prospeccao/telefonia.py`: incorporar seletivamente as rotinas de `ligacoes.py`, `roteiros_voz.py` e `servidor_voz.py` com testes, sem copiar a estrutura antiga da `DevC`.
- `prospeccao/auditoria.py`: armazenar estados, aprovação, idempotência e referências da chamada.
- Endpoints internos específicos e protegidos; a API pública de cotação não deve ter acesso a tokens de telefonia.

**Implantação:** o servidor atual atende `127.0.0.1`, mas um painel remoto precisa de infraestrutura de autenticação, autorização, HTTPS, armazenamento de estados, webhooks verificados e segredos mantidos apenas no servidor. Não expor Twilio/LLM ou relatórios completos no frontend.

## 5. Contratos de dados e API propostos

**Snapshot mínimo do relatório:** `report_id`, `empresa_id`, `unidade_id`, `created_at`, `report_version`, `hash`, `plano_recomendado`, `coberturas_presentes`, `prioridades_evidenciadas`, `confianca`, `ressalvas`, `pendencias` e `fonte_dos_dados`.

**Contexto para a IA (lista positiva de campos):** identificador não sensível, nome comercial revisado, ramo de atividade, localidade em nível apropriado, nome do plano preliminar, coberturas confirmadas, duas prioridades e seus motivos, pendências e avisos obrigatórios. **Nunca enviar** CSVs inteiros, documentos, telefone, CPF/CNPJ, contatos, endereços completos, tokens ou outras informações fora da finalidade. Usar provedor de IA apenas depois de estabelecer as bases e os controles de tratamento de dados.

**Rascunho gerado:** `script_id`, `report_id`, `report_hash`, `texto`, `versao`, `fatos_utilizados`, `avisos`, `aprovado_por`, `aprovado_em` e `status`. Aprovação só vale para o texto exato e o hash do relatório; alterações invalidam a aprovação.

**Endpoints sugeridos**, todos internos e autorizados:

- `GET /api/interno/relatorios/:id` — relatório seguro do colaborador;
- `POST /api/interno/relatorios/:id/roteiros` — gerar rascunho, **sem telefonar**;
- `PATCH /api/interno/roteiros/:id` — editar texto e invalidar aprovação anterior;
- `POST /api/interno/roteiros/:id/aprovar` — gravar aprovação e hash;
- `POST /api/interno/roteiros/:id/ligacoes` — solicitação de **uma** chamada com idempotência;
- `GET /api/interno/ligacoes/:id` — estado e histórico;
- `POST /webhooks/twilio/voz` — receber eventos verificados por assinatura.

## 6. Regras e limites do roteiro

- Dizer que se trata de **contato automatizado com voz sintética**, identificar a empresa responsável e a finalidade. Não fingir ser o colaborador.
- Usar tom consultivo, preferencialmente curto, e oferecer canal humano.
- Nunca inventar prêmio, preço, desconto, franquia, limite contratual, promessa de cobertura, sinistro provável, aprovação ou contratação.
- Não afirmar que o cliente está segurado; o plano é preliminar e depende da cotação, análise de elegibilidade e condições oficiais.
- Não utilizar como fato risco territorial desconhecido, referências domiciliares incompatíveis ou indicadores sem validação.
- Não transformar pontuação relativa em probabilidade de roubo, acidente ou sinistro.
- Se faltarem informações para uma proposta fiel, gerar somente mensagem de **convite para esclarecimentos**; sem oferta específica.
- Validar o texto final inclusive **após a edição humana**; obedecer ao limite da Twilio/TwiML e ao tipo de ligação disponibilizado.
- Antes de ligar, aplicar permissões de equipe, base legal/consentimento e preferências de não contato, observando LGPD e regras aplicáveis à telefonia comercial.
- Não executar campanhas em lote, chamadas automáticas por evento, gravação ou transcrição por padrão.

## 7. Estados e segurança operacional

`RASCUNHO -> EM_REVISAO -> APROVADO -> SOLICITADO -> EM_CURSO -> (CONCLUIDO | OCUPADO | SEM_RESPOSTA | FALHA | RESULTADO_INDETERMINADO)`.

Uma falha de rede no envio pode significar que a operadora **já recebeu o pedido**. Nessas situações, classificar como `RESULTADO_INDETERMINADO`, consultar logs/status por ID e **não rediscar automaticamente**.

Usar idempotency key por comando, controle de concorrência, logs sem números completos, retenção limitada e verificações de assinatura em webhooks. Restringir leitura de relatório e gravação de chamadas conforme equipe/unidade. Tokens Twilio, LLM e chaves de webhook permanecem no backend e fora do Git.

## 8. Fases de implementação

| Fase | Entrega | Condição de aceite |
|---|---|---|
| 0 | Contratos de dados e arquitetura do painel | Campos sensíveis bloqueados, segregação de endpoints e relatório versionado |
| 1 | Portar componentes Twilio da branch `codigo-ligacao` | Testes isolados com mocks; sem chamadas reais automáticas |
| 2 | Painel interno e relatório | Tela separada em `/interno`, autenticação/permissões e relatório auditável |
| 3 | Gerador de roteiro por IA | Somente fatos permitidos, validação de alegações, fallback determinístico |
| 4 | Aprovação e ligação individual | Prévia editável, validação de destino, consentimento e envio explícito |
| 5 | Histórico e estados | Persistência, idempotência, status, tratamento de resultado incerto |
| 6 | Homologação | Testes end-to-end em ambiente controlado, revisão de privacidade e piloto autorizado |

## 9. Testes obrigatórios

1. Relatório inválido, incompleto ou sem permissão **não** autoriza gerar ou iniciar chamada.
2. Saída de IA com preço inventado, cobertura inexistente ou promessa contratual é **rejeitada**.
3. Mudança no relatório ou no texto invalida a aprovação anterior.
4. Ausência de autorização/consentimento aplicável, telefone inválido ou número bloqueado impede ligação.
5. Clique duplo, timeout ou webhook duplicado não causam chamadas duplicadas.
6. Testes do adaptador Twilio são simulados (mocks), sem consumo de créditos ou minutos.
7. Identificadores pessoais, credenciais e conteúdo completo do relatório não aparecem em URL, logs ou corpo enviado à Twilio.
8. A integração não altera os resultados determinísticos do motor de seguros.
9. Os workflows GitHub Actions passam no Python 3.12/3.13 e nos testes Node.
10. Uma chamada real só ocorre em piloto autorizado, com destino verificado e orçamento/limites configurados.

## 10. Decisões explícitas

- **Já existe:** motor e relatório da `main`; telefonia de demonstração na `codigo-ligacao`.
- **Será desenvolvido:** painel interno real, geração por IA, aprovação, segurança, persistência e adaptação Twilio.
- **Não confundir:** TTS lendo um roteiro de IA **não é** agente conversacional autônomo. Caso se queira diálogo bidirecional, criar projeto e critérios próprios para áudio em tempo real, transcrição, transferência a humano, limites de decisão, autorização, latência e proteção de dados.
- **Sequência de Git recomendada:** criar branch `feature/ligacoes-ia-painel` a partir da `main`, trazer **seletivamente** componentes e testes da `codigo-ligacao`, validar e integrar por PR. Preservar `codigo-ligacao` como referência histórica até o fim da homologação.
