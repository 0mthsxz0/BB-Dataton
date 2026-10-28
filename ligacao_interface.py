"""Tela compartilhada entre o aplicativo principal e a execução independente."""
import streamlit as st

from ligacoes import ClienteLigacoes, Configuracao, ErroLigacao, ResultadoIncerto, criar_twiml, validar_telefone


def renderizar():
    st.title("Ligações por telefone")
    st.write("Ligue para uma pessoa e reproduza uma mensagem com voz em português.")
    st.caption("Twilio Voice · no teste grátis: destinos verificados no mesmo país, até 75 minutos e 30 dias. "
               "A disponibilidade depende da conta. Chamadas em conta paga consomem saldo.")
    try:
        config = Configuracao.do_ambiente()
    except ValueError as erro:
        st.info(str(erro))
        st.code('$env:TWILIO_ACCOUNT_SID="AC..."\n$env:TWILIO_AUTH_TOKEN="..."\n'
                '$env:TWILIO_FROM_NUMBER="+..."', language="powershell")
        st.write("Use o número de origem fornecido/autorizado pela Twilio. Veja LIGACOES.md para configurar.")
        return
    cliente = ClienteLigacoes(config)
    bloqueado = st.session_state.get("envio_incerto", False)
    ativa = st.session_state.get("chamada_ativa", False)
    if bloqueado:
        st.warning("O último envio ficou sem confirmação. Verifique os logs de Voice no console antes de liberar outra chamada.")
        if st.button("Já conferi os logs; liberar novo envio"):
            st.session_state.envio_incerto = False
            st.rerun()
    with st.form("nova_ligacao"):
        destino = st.text_input("Telefone de destino", placeholder="+55DDDNUMERO")
        mensagem = st.text_area("Mensagem que será falada", max_chars=1500,
            value="Olá! Esta é uma ligação de teste do nosso projeto. Obrigado por atender.")
        limite = st.number_input("Duração máxima (segundos)", min_value=10, max_value=600, value=120, step=10)
        autorizado = st.checkbox("Conferi o telefone e a pessoa está de acordo em receber esta ligação.")
        enviar = st.form_submit_button("Ligar agora", type="primary", disabled=bloqueado or ativa)
    if enviar:
        if not autorizado:
            st.error("Confirme o telefone e a autorização antes de ligar.")
        else:
            try:
                validar_telefone(destino)
                criar_twiml(mensagem)
                # O formulário não deve reenviar em reruns ou após resposta incerta.
                st.session_state.envio_incerto = True
                resultado = cliente.ligar(destino, mensagem, int(limite))
                st.session_state.ultima_chamada = resultado
                st.session_state.chamada_ativa = True
                st.session_state.envio_incerto = False
                st.rerun()
            except ResultadoIncerto as erro:
                st.error(str(erro))
                st.rerun()
            except (ValueError, ErroLigacao) as erro:
                st.session_state.envio_incerto = False
                st.error(str(erro))
    chamada = st.session_state.get("ultima_chamada")
    if chamada:
        st.subheader("Última chamada desta sessão")
        st.code(chamada["sid"], language=None)
        st.write("Status:", chamada.get("status") or "não informado")
        st.caption("Uma solicitação aceita não garante que a pessoa atendeu. Atualize para consultar o resultado.")
        a, b = st.columns(2)
        atualizar = a.button("Atualizar status")
        encerrar = b.button("Encerrar chamada", disabled=not st.session_state.get("chamada_ativa", False))
        if atualizar or encerrar:
            try:
                resultado = (cliente.encerrar if encerrar else cliente.consultar)(chamada["sid"])
                st.session_state.ultima_chamada = resultado
                st.session_state.chamada_ativa = resultado.get("status") not in {
                    "completed", "canceled", "failed", "busy", "no-answer"}
                st.rerun()
            except (ValueError, ErroLigacao) as erro:
                st.error(str(erro))


if __name__ == "__main__":
    st.set_page_config(page_title="Ligações | Protege Empresa", page_icon="📞")
    renderizar()
