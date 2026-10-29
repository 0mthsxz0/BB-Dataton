# Iniciar a demonstracao local

Pare o servidor antigo com Ctrl+C e abra `Iniciar-Demonstracao-Local.cmd` na raiz do projeto.

Na primeira abertura, informe uma senha interna de pelo menos 12 caracteres, o Account SID iniciado por AC e o Auth Token atual da Twilio. Use credenciais reais da sua conta; nao compartilhe esses valores em capturas de tela.

O atalho salva as opcoes em `.env.local.json`, ignorado pelo Git. Esse arquivo contem segredos: nao envie nem publique. Para trocar uma credencial, edite somente seu valor nesse arquivo e reinicie pelo atalho. As configuracoes tambem sao lidas pelo comando normal `npm --prefix frontend start`; variaveis ja definidas no terminal tem prioridade.

O atalho habilita a consulta local por ID e o envio de chamadas, mantendo a senha interna, o acesso apenas em localhost e a aprovacao individual do roteiro e do contato na tela. Chamadas reais podem consumir o saldo da Twilio.

O modo inicial e trial. Nesse modo, o atalho inicia o servidor de voz na porta 8765, reutiliza um tunel ngrok HTTPS para essa porta ou tenta iniciar `ngrok http 8765`. O ngrok precisa estar instalado e autenticado. A URL atual e salva automaticamente com `/voz.xml`. O destino deve estar verificado na Twilio.

O site abre na porta 4183. Se ela estiver ocupada, o atalho pede para encerrar o servidor antigo e executar novamente. Os auxiliares de voz e ngrok iniciados em segundo plano permanecem abertos quando o site e encerrado, sendo reutilizados na proxima abertura.

Para uma conta em modo completo, altere `TWILIO_MODE` para `completo`; o atalho pedira o numero de origem autorizado na proxima abertura. Nao altere o modo apenas para contornar uma restricao de conta trial.
