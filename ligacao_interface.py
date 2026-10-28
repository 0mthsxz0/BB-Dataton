"""Tela de ligação com edição, template por relatório e roteiro por chamada."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import streamlit as st

from ligacoes import ClienteLigacoes, Configuracao, ErroLigacao, ResultadoIncerto, criar_twiml, validar_telefone
from mensagens_prospeccao import TEMPLATE_BASE, json_seguro, preencher_template, variaveis_relatorio
from roteiros_voz import salvar_roteiro, url_roteiro


def preparar_mensagem(contexto):
    assinatura = hashlib.sha256(json.dumps(json_seguro(contexto), sort_keys=True,
        ensure_ascii=False).encode()).hexdigest()[:20]
    prefixo = 'relatorio_' + assinatura
    editor = prefixo + '_mensagem'
    registro, pontos, plano = (contexto[k] for k in ('registro', 'pontuacoes', 'recomendacao'))
    base = variaveis_relatorio(registro, pontos, plano)
    st.subheader('Mensagem a partir da recomendação')
    st.caption(f'Empresa: {registro.get("empresa_id", "")} · Estabelecimento: {registro.get("imovel_id", "")} · Plano: {base["plano"]}')
    with st.form(prefixo + '_modelo'):
        empresa = st.text_input('Nome da empresa para a ligação', value=base['empresa'], max_chars=120,
            help='Confirme o nome comercial. Quando a base não traz o nome, o identificador aparece como referência.')
        contato = st.text_input('Nome do contato (opcional)', max_chars=80)
        colaborador = st.text_input('Nome do colaborador (opcional)', max_chars=80)
        organizacao = st.text_input('Equipe ou organização (opcional)', max_chars=100)
        with st.expander('Editar o modelo com variáveis'):
            modelo = st.text_area('Modelo base', value=TEMPLATE_BASE, max_chars=5000, height=200)
            st.caption('Variáveis disponíveis: ' + ', '.join('{' + k + '}' for k in base))
        gerar = st.form_submit_button('Gerar mensagem do relatório')
    variaveis = variaveis_relatorio(registro, pontos, plano, empresa=empresa,
        contato=contato, colaborador=colaborador, organizacao=organizacao)
    if gerar or editor not in st.session_state:
        try:
            st.session_state[editor] = preencher_template(modelo, variaveis)
            st.session_state[editor + '_consentimento'] = False
        except ValueError as erro:
            st.error(str(erro))
            if editor not in st.session_state:
                st.session_state[editor] = ''
    with st.expander('Conferir dados usados na mensagem'):
        st.json(variaveis)
        st.caption('O texto é preenchido por template. Nenhum modelo de IA externo é chamado. '
                   'As notas representam prioridade de proteção, não probabilidade de sinistro.')
        st.dataframe([{'Cobertura': p['nome'], 'Prioridade': p['prioridade'],
                       'Confiança': p.get('confianca')}
                      for c, p in pontos.items() if c in plano.get('coberturas', [])], hide_index=True)
    return editor


def mensagem_inicial():
    try:
        return Path(__file__).with_name('mensagem_ligacao.txt').read_text(encoding='utf-8-sig').strip()
    except OSError:
        return 'Olá! Esta é uma ligação de teste do nosso projeto. Obrigado por atender.'


def renderizar(contexto=None):
    st.title('Ligações por telefone')
    st.caption('Twilio Voice · no teste grátis: destinos verificados no mesmo país. '
               'Limites e disponibilidade são controlados pela conta Twilio.')
    editor = preparar_mensagem(contexto) if contexto else 'ligacao_livre_mensagem'
    if contexto and st.button('Nova ligação sem relatório'):
        st.session_state.pop('contexto_ligacao', None)
        st.rerun()
    try:
        config = Configuracao.do_ambiente()
    except ValueError as erro:
        if contexto:
            st.text_area('Mensagem que será falada', key=editor, max_chars=1500, height=230)
        st.info(str(erro))
        st.code('$env:TWILIO_ACCOUNT_SID="AC..."\n$env:TWILIO_AUTH_TOKEN="..."', language='powershell')
        st.write('Configure a URL HTTPS de voz para editar a fala no teste grátis. Veja VOZ_PERSONALIZADA.md.')
        return
    trial = config.modo == 'trial'
    personalizavel = not trial or bool(config.twiml_url)
    if trial and config.twiml_url:
        st.info('Fala personalizada: revise a mensagem abaixo antes de ligar. '
                'Cada envio guarda um roteiro próprio por até uma hora. Mantenha o servidor de voz e o ngrok ligados.')
    elif trial:
        st.info('Modo teste sem URL própria: a Twilio reproduzirá sua demonstração. '
                'Para usar a mensagem desta tela, configure TWILIO_TWIML_URL com o HTTPS do nosso servidor terminado em /voz.xml.')
        if contexto:
            st.text_area('Prévia da mensagem do relatório', key=editor, max_chars=1500, height=230)
    else:
        st.write('Modo completo: a mensagem será lida em português. Chamadas e voz podem consumir saldo.')
    cliente = ClienteLigacoes(config)
    bloqueado = st.session_state.get('envio_incerto', False)
    ativa = st.session_state.get('chamada_ativa', False)
    if bloqueado:
        st.warning('O último envio ficou sem confirmação. Verifique os logs de Voice antes de liberar outra chamada.')
        if st.button('Já conferi os logs; liberar novo envio'):
            st.session_state.envio_incerto = False
            st.rerun()
    with st.form(editor + '_ligacao'):
        destino = st.text_input('Telefone de destino', placeholder='+55DDDNUMERO', key=editor + '_destino')
        mensagem = ''
        limite = None
        if personalizavel:
            if editor not in st.session_state:
                st.session_state[editor] = mensagem_inicial()
            mensagem = st.text_area('Mensagem que será falada', key=editor, max_chars=1500, height=230)
            st.caption('Confira a identificação, a empresa, o roteiro e o telefone. '
                       'A chamada reproduz exatamente o texto revisado, respeitando o processamento de voz da Twilio.')
        if not trial:
            limite = int(st.number_input('Duração máxima (segundos)', min_value=10, max_value=600, value=120, step=10))
        else:
            st.caption('Use um destino verificado. Os limites de duração e minutos são controlados pela Twilio.')
        autorizado = st.checkbox('Conferi o telefone, revisei a mensagem e a pessoa está de acordo em receber esta ligação.',
            key=editor + '_consentimento')
        enviar = st.form_submit_button('Ligar agora', type='primary',
            disabled=bloqueado or ativa or bool(contexto and not personalizavel))
    if enviar:
        if not autorizado:
            st.error('Confirme o telefone, a mensagem e a autorização antes de ligar.')
        else:
            try:
                validar_telefone(destino)
                config_envio = config
                if personalizavel:
                    criar_twiml(mensagem)
                if trial and personalizavel:
                    # Validar a URL antes de salvar e não alterar o arquivo TXT compartilhado.
                    url_roteiro(config.twiml_url, '0' * 64)
                    identificador = salvar_roteiro(mensagem)
                    config_envio = replace(config, twiml_url=url_roteiro(config.twiml_url, identificador))
                st.session_state.envio_incerto = True
                resultado = ClienteLigacoes(config_envio).ligar(destino,
                    mensagem if not trial else '', limite)
                if contexto:
                    resultado['referencia'] = str(contexto['registro'].get('empresa_id', ''))
                st.session_state.ultima_chamada = resultado
                st.session_state.chamada_ativa = True
                st.session_state.envio_incerto = False
                st.rerun()
            except ResultadoIncerto:
                st.session_state.envio_incerto = True
                st.rerun()
            except (ValueError, ErroLigacao) as erro:
                st.session_state.envio_incerto = False
                st.error(str(erro))
            except OSError:
                st.session_state.envio_incerto = False
                st.error('Não foi possível guardar o roteiro local. Confira a permissão de escrita da pasta tmp/roteiros_voz.')
    chamada = st.session_state.get('ultima_chamada')
    if chamada:
        st.subheader('Última chamada desta sessão')
        if chamada.get('referencia'):
            st.caption('Empresa da chamada: ' + chamada['referencia'])
        st.code(chamada['sid'], language=None)
        st.write('Status:', chamada.get('status') or 'não informado')
        st.caption('Uma solicitação aceita não garante atendimento. Atualize para consultar o resultado.')
        a, b = st.columns(2)
        atualizar = a.button('Atualizar status')
        encerrar = b.button('Encerrar chamada', disabled=not st.session_state.get('chamada_ativa', False))
        if atualizar or encerrar:
            try:
                resultado = (cliente.encerrar if encerrar else cliente.consultar)(chamada['sid'])
                if chamada.get('referencia'):
                    resultado['referencia'] = chamada['referencia']
                st.session_state.ultima_chamada = resultado
                st.session_state.chamada_ativa = resultado.get('status') not in {
                    'completed', 'canceled', 'failed', 'busy', 'no-answer'}
                st.rerun()
            except (ValueError, ErroLigacao) as erro:
                st.error(str(erro))


if __name__ == '__main__':
    st.set_page_config(page_title='Ligações | Protege Empresa', page_icon='📞')
    renderizar()
