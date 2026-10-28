"""Interface web em português. Execute: streamlit run app.py."""
from __future__ import annotations

from pathlib import Path
import copy
import io
import json
import os
import zipfile
import pandas as pd
import plotly.express as px
import streamlit as st

from exportacao import analisar_base, csv_bytes
from motor_pontuacao import DECISORIAS, ROUBO, MotorPontuacao, carregar_config
from processamento import ARQUIVOS, carregar_base, localizar_dados, localizar_referencias
from recomendador import recomendar_plano

st.set_page_config(page_title='Protege Empresa | Datathon', page_icon='🛡️', layout='wide')
st.markdown('''<style>
 .stApp {background:linear-gradient(135deg,#f7f9fd,#eef3fc)}
 [data-testid="stSidebar"] {background:#112b56;color:#fff}
 [data-testid="stSidebar"] p,[data-testid="stSidebar"] label,
 [data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
 [data-testid="stSidebar"] h3 {color:#fff}
 [data-testid="stMetric"] {background:white;border:1px solid #dce4f1;border-radius:14px;padding:18px}
 h1 {letter-spacing:-1.1px;color:#112b56}
 .eyebrow {font-size:12px;font-weight:750;letter-spacing:2px;color:#1456e8}
 .hero {border-left:5px solid #f4d84c;padding:12px 20px;background:#fff;border-radius:0 12px 12px 0;margin-bottom:24px}
 .hero p {margin:0;color:#52647e}
 .stButton>button {border-radius:9px}
 @media (max-width:1100px) {
   [data-testid="stHorizontalBlock"] {flex-wrap:wrap}
   [data-testid="stColumn"] {flex:1 1 calc(50% - 1rem)!important;min-width:0!important}
 }
 @media (max-width:700px) {
   [data-testid="stColumn"] {flex:1 1 100%!important}
 }
 </style>''', unsafe_allow_html=True)


def assinatura(pasta, externo, referencias='', confirmacoes=''):
    caminhos = [Path(pasta) / f'{n}.csv' for n in ARQUIVOS]
    if externo:
        caminhos.append(Path(externo))
    if referencias:
        caminhos.extend(sorted(Path(referencias).glob('*.csv')))
    if confirmacoes:
        caminhos.append(Path(confirmacoes))
    return tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in caminhos)


@st.cache_data(show_spinner='Organizando os dados…')
def obter_base(pasta, externo, versao_arquivos, referencias='',confirmacoes=''):
    return carregar_base(pasta, externo or None, referencias or None, confirmacoes or None)


@st.cache_data(show_spinner='Analisando os estabelecimentos…')
def obter_resumo(pasta, externo, versao_arquivos, config_json,referencias='',confirmacoes=''):
    base = carregar_base(pasta, externo or None,referencias or None,confirmacoes or None)
    motor = MotorPontuacao(base, json.loads(config_json))
    linhas = []
    for r in base.estabelecimentos.to_dict('records'):
        pontos = motor.analisar_registro(r)
        plano = recomendar_plano(pontos, base.catalogo, motor.config, r)
        linha = {c: r.get(c) for c in ['empresa_id', 'imovel_id', 'grupo_atividade', 'porte', 'municipio_real', 'uf_real']}
        linha.update(plano=plano['plano_recomendado'], confianca=plano['confianca_geral'],
                     elegivel=plano['elegibilidade']['elegivel'], estavel=plano['recomendacao_estavel'])
        linha.update({c: s['prioridade'] for c, s in pontos.items()})
        linhas.append(linha)
    return pd.DataFrame(linhas)


def dinheiro(valor):
    if valor is None:
        return 'Não observado'
    return f'R$ {valor:,.0f}'.replace(',', '.')


def grafico(pontos):
    df = pd.DataFrame([{'Cobertura': s['nome'], 'Prioridade': s['prioridade'],
                        'Confiança': s['confianca'], 'Tipo': 'Índice de decisão'}
                       for s in pontos.values()])
    fig = px.bar(df.sort_values('Prioridade'), x='Prioridade', y='Cobertura', orientation='h',
                 color='Tipo', color_discrete_map={'Índice de decisão': '#1456e8'},
                 hover_data=['Confiança'], range_x=[0, 100])
    fig.update_layout(height=450, margin=dict(l=0,r=10,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)',
                      plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation='h', y=1.1))
    return fig


def seletor(base, chave='principal'):
    df = base.estabelecimentos
    grupos = ['Todos'] + sorted(df.grupo_atividade.unique())
    with st.expander('Filtrar por atividade, porte ou CNAE'):
        grupo = st.selectbox('Atividade', grupos, key='grupo_' + chave)
        porte = st.selectbox('Porte', ['Todos'] + sorted(df.porte.unique()), key='porte_' + chave)
        busca = st.text_input('Buscar por empresa, estabelecimento ou CNAE', key='busca_' + chave).strip()
    filtrado = df
    if grupo != 'Todos':
        filtrado = filtrado.loc[filtrado.grupo_atividade.eq(grupo)]
    if porte != 'Todos':
        filtrado = filtrado.loc[filtrado.porte.eq(porte)]
    if busca:
        mascara = filtrado[['empresa_id', 'imovel_id', 'cnae_principal', 'descricao_cnae']].astype(str).apply(
            lambda s: s.str.contains(busca, case=False, regex=False)).any(axis=1)
        filtrado = filtrado.loc[mascara]
    if filtrado.empty:
        st.info('Nenhum estabelecimento encontrado com esses filtros.')
        return None
    ids = filtrado.imovel_id.tolist()
    registros = filtrado.set_index('imovel_id')
    imovel = st.selectbox('Estabelecimento', ids, key='imovel_' + chave,
        format_func=lambda i: f'{i} · {registros.loc[i, "grupo_atividade"]} · {registros.loc[i, "municipio_real"]}')
    return filtrado.loc[filtrado.imovel_id.eq(imovel)].iloc[0].to_dict()


def detalhar(registro, base, config):
    motor = MotorPontuacao(base, config)
    pontos = motor.analisar_registro(registro)
    plano = recomendar_plano(pontos, base.catalogo, config, registro)
    st.subheader(f'{registro["imovel_id"]} · {registro["grupo_atividade"]}')
    st.caption(f'{registro["empresa_id"]} · CNAE {registro["cnae_principal"]} · {registro["municipio_real"]}/{registro["uf_real"]}')
    a, b, c = st.columns(3)
    a.metric('Plano sugerido', plano['plano_recomendado'])
    b.metric('Confiança dos dados', f'{plano["confianca_geral"]:.0%}')
    c.metric('Aceitação contratual', plano['elegibilidade']['elegivel'])
    st.info(plano['justificativa'])
    if not plano['recomendacao_estavel']:
        st.warning(f'Sensível à incerteza dos dados: cenários variam entre {plano["plano_cenario_inferior"]} e {plano["plano_cenario_superior"]}.')
    st.plotly_chart(grafico(pontos), use_container_width=True)
    st.caption('Somente quatro índices decidem o plano. Nota maior indica maior prioridade; não é probabilidade de sinistro.')
    with st.expander('Valores das nove coberturas do catálogo'):
        dimensoes=motor.dimensionar_coberturas(registro)
        st.dataframe(pd.DataFrame([{'Cobertura':x['nome'],'Papel':x['papel'],
            'Cenário mínimo':dinheiro(x['faixa_valor_min']),'Cenário máximo':dinheiro(x['faixa_valor_max']),
            'Observação':x['justificativa']} for x in dimensoes.values()]),hide_index=True,use_container_width=True)
    st.subheader('Entenda o cálculo')
    codigo = st.selectbox('Cobertura', list(pontos), format_func=lambda c: pontos[c]['nome'])
    s = pontos[codigo]
    a,b,c,d = st.columns(4)
    a.metric('Evento · relativo', f'{s["risco_evento_relativo"]:.3f}')
    b.metric('Impacto · normalizado', f'{s["impacto_normalizado"]:.3f}')
    c.metric('Vulnerabilidade · proxy', f'{s["vulnerabilidade"]:.3f}')
    d.metric('Prioridade · 0 a 100', f'{s["prioridade"]:.1f}')
    st.write('Valor exposto no cenário:', dinheiro(s['valor_exposto_brl']))
    st.write(f'Sensibilidade à evidência incompleta: {s["prioridade_min"]:.1f} a {s["prioridade_max"]:.1f}. Não é intervalo estatístico.')
    st.dataframe(pd.DataFrame(s['fatores_evento']).astype(str), hide_index=True, use_container_width=True)
    with st.expander('Fonte, período e abrangência do indicador'):
        st.json(s['referencia_evento'])
        st.caption('Referências municipais não distinguem bairros ou ruas. Dados de vitimização domiciliar são uma proxy contextual para empresas.')
    with st.expander('Fórmula, impacto e interações'):
        st.code(s['formula'], language='text')
        st.json({'impacto':s['fator_impacto'], 'vulnerabilidade':s['fator_vulnerabilidade'],
                 'decomposicao':s['decomposicao']})
    for limitacao in s['limitacoes']:
        st.caption('• ' + limitacao)
    st.subheader('Comparação dos planos')
    st.dataframe(pd.DataFrame(plano['comparacao']).astype(str), hide_index=True, use_container_width=True)
    with st.expander('Informações prioritárias a confirmar'):
        for pergunta in plano['perguntas_confirmacao']:
            st.write('• ' + pergunta)
    return pontos, plano


def main():
    padrao_config=carregar_config()
    if 'config_regras' not in st.session_state or st.session_state.config_regras.get('versao')!=padrao_config['versao']:
        st.session_state.config_regras = padrao_config
    config = st.session_state.config_regras
    st.sidebar.markdown('## Protege Empresa')
    st.sidebar.caption('Datathon · recomendação explicável')
    pagina = st.sidebar.radio('Navegação', ['Visão geral', 'Analisar estabelecimento', 'Comparar',
                                           'Simular cenários', 'Regras e metodologia', 'Exportar'])
    try:
        padrao = str(localizar_dados(os.environ.get('BB_DATATHON_DADOS')))
    except ValueError:
        padrao = str(Path(__file__).parent / 'data' / 'desenvolvimento')
    with st.sidebar.expander('Fonte de dados'):
        pasta = st.text_input('Pasta dos nove CSVs', padrao)
        externo = st.text_input('CSV territorial opcional', '')
        ref_padrao=localizar_referencias()
        referencias=st.text_input('Pasta de referências públicas',str(ref_padrao))
        confirmacoes=st.text_input('CSV de confirmações por unidade (opcional)','')
    st.sidebar.caption('Protótipo acadêmico. Dados fictícios. Sem vínculo oficial com a seguradora.')
    st.markdown('<div class="eyebrow">PROTEÇÃO QUE FAZ SENTIDO</div>', unsafe_allow_html=True)
    st.title(pagina)
    st.markdown('<div class="hero"><p>Dados da empresa, consequências financeiras e decisões que você consegue explicar.</p></div>', unsafe_allow_html=True)
    try:
        versao = assinatura(pasta, externo,referencias,confirmacoes)
        base = obter_base(pasta, externo, versao,referencias,confirmacoes)
        config_json = json.dumps(config, sort_keys=True)
        motor = MotorPontuacao(base, config)
    except (OSError, ValueError, KeyError) as erro:
        st.error(str(erro))
        st.code('python scripts/importar_dados.py "CAMINHO_DOS_CSVS"')
        st.stop()

    if pagina == 'Visão geral':
        resumo = obter_resumo(pasta, externo, versao, config_json,referencias,confirmacoes)
        a,b,c,d = st.columns(4)
        a.metric('Empresas', f'{resumo.empresa_id.nunique():,}'.replace(',', '.'))
        b.metric('Estabelecimentos', f'{len(resumo):,}'.replace(',', '.'))
        c.metric('Baixa confiança (< 50%)', f'{resumo.confianca.lt(.5).mean():.0%}')
        d.metric('Sensíveis à incerteza', f'{(~resumo.estavel).mean():.0%}')
        st.subheader('Planos sugeridos')
        contagem = resumo.plano.value_counts().rename_axis('Plano').reset_index(name='Estabelecimentos')
        st.plotly_chart(px.bar(contagem,x='Plano',y='Estabelecimentos',color='Plano',
            color_discrete_sequence=['#1456e8','#f4d84c','#112b56']),use_container_width=True)
        st.subheader('Os quatro índices que diferenciam os planos')
        medias = pd.DataFrame([{'Cobertura': config['coberturas'][c]['nome'], 'Prioridade':resumo[c].mean()} for c in DECISORIAS])
        st.plotly_chart(px.bar(medias,y='Cobertura',x='Prioridade',orientation='h',range_x=[0,100],
            color_discrete_sequence=['#1456e8']),use_container_width=True)
        for aviso in base.avisos:
            st.warning(aviso)
        st.caption('Todos os planos são sugestões condicionais à elegibilidade. Preços e condições contratuais pendentes.')
        st.dataframe(resumo[['empresa_id','imovel_id','grupo_atividade','municipio_real','plano','confianca','elegivel']],
                     hide_index=True,use_container_width=True)

    elif pagina == 'Analisar estabelecimento':
        registro = seletor(base)
        if registro:
            detalhar(registro, base, config)

    elif pagina == 'Comparar':
        esquerda,direita = st.columns(2)
        with esquerda:
            st.subheader('Estabelecimento A')
            a = seletor(base,'comparar_a')
        with direita:
            st.subheader('Estabelecimento B')
            b = seletor(base,'comparar_b')
        if a and b:
            sa,sb = motor.analisar_registro(a),motor.analisar_registro(b)
            pa = recomendar_plano(sa,base.catalogo,config,a)
            pb = recomendar_plano(sb,base.catalogo,config,b)
            esquerda.metric('Plano A',pa['plano_recomendado'])
            direita.metric('Plano B',pb['plano_recomendado'])
            comparacao = pd.DataFrame([{'Cobertura':s['nome'],'Prioridade A':s['prioridade'],
                                       'Prioridade B':sb[c]['prioridade'], 'Diferença B − A':sb[c]['prioridade']-s['prioridade']}
                                      for c,s in sa.items()])
            st.plotly_chart(px.bar(comparacao,x='Cobertura',y=['Prioridade A','Prioridade B'],barmode='group',
                color_discrete_sequence=['#1456e8','#d5af00'],range_y=[0,100]),use_container_width=True)
            st.dataframe(comparacao,hide_index=True,use_container_width=True)
            st.write('Motivo A:',pa['justificativa'])
            st.write('Motivo B:',pb['justificativa'])

    elif pagina == 'Simular cenários':
        registro = seletor(base,'simular')
        if registro:
            st.info('Simulações alteram apenas esta visualização. Os CSVs originais permanecem preservados.')
            simulado = copy.deepcopy(registro)
            multiplicador = st.slider('Multiplicador do valor dos bens',.1,10.,1.,.1)
            for campo in ['bens_ponderados','bens_total_referencia','equipamentos_ponderados',
                          'equipamentos_total_referencia','informatica_ponderada','cozinha_ponderada']:
                if simulado.get(campo) is not None:
                    simulado[campo] = float(simulado[campo])*multiplicador
            usar_cidade = st.checkbox('Simular um indicador territorial hipotético')
            if usar_cidade:
                simulado['seguranca_da_cidade_0_1'] = st.slider('Segurança relativa hipotética',0.,1.,.9,.01)
                simulado['confianca_seguranca_0_1'] = .5
                simulado['fonte_seguranca'] = 'SIMULAÇÃO; não é dado observado'
            if st.checkbox('Simular reposição de vidros confirmada'):
                simulado['possui_vidros_confirmado']='SIM'
                simulado['valor_vidros_reposicao_brl']=st.number_input('Valor hipotético de reposição dos vidros (R$)',min_value=0.,value=10000.,step=1000.)
            clima=st.selectbox('Cenário climático',['Principal','2016–2025','Rajadas 40/60 km/h'])
            coluna={'2016–2025':'exposicao_climatica_2016_2025','Rajadas 40/60 km/h':'exposicao_climatica_limiares_40_60'}.get(clima)
            if coluna:
                if registro.get(coluna) is not None:
                    simulado['exposicao_climatica_0_1']=registro[coluna]
                    simulado['periodo_clima']='SIMULAÇÃO: '+clima
                else:
                    st.warning('Sem série climática preparada para este cenário.')
            original,novo = motor.analisar_registro(registro),motor.analisar_registro(simulado)
            st.dataframe(pd.DataFrame([{'Cobertura':s['nome'],'Original':s['prioridade'],
                'Simulado':novo[c]['prioridade'],'Mudança':novo[c]['prioridade']-s['prioridade']}
                for c,s in original.items()]),hide_index=True,use_container_width=True)
            st.caption('Alterar patrimônio afeta impacto; não altera automaticamente o componente do evento de roubo.')
            p = recomendar_plano(novo,base.catalogo,config,simulado)
            st.metric('Plano no cenário',p['plano_recomendado'])

    elif pagina == 'Regras e metodologia':
        st.write('Modelo transparente com interação entre evento, impacto e vulnerabilidade. Todos os parâmetros são hipóteses da equipe.')
        st.code('P = 100 × clip[(p+(1−p)I) × (a+(1−a)R) × (b+(1−b)V) + kIRD, 0, 1]',language='text')
        st.caption('R: evento relativo; I: impacto normalizado; V: vulnerabilidade limitada pelos dados; D: interação específica.')
        st.info('As cinco coberturas comuns são dimensionadas e exportadas. Somente roubo, vendaval, RC empregador e vidros influenciam a escolha. Mudanças nos limiares climáticos exigem regenerar as referências com o script de preparo.')
        novo = st.text_area('Configuração JSON',json.dumps(config,ensure_ascii=False,indent=2),height=420)
        a,b = st.columns(2)
        if a.button('Validar e aplicar regras',type='primary'):
            try:
                st.session_state.config_regras = carregar_config(json.loads(novo))
                st.success('Regras válidas. Resultados serão recalculados.')
                st.rerun()
            except (ValueError,KeyError,TypeError) as erro:
                st.error(f'Configuração rejeitada: {erro}')
        if b.button('Restaurar configuração original'):
            st.session_state.config_regras = carregar_config()
            st.rerun()
        st.download_button('Baixar configuração ativa',json.dumps(config,ensure_ascii=False,indent=2),
                           file_name='config_regras.json',mime='application/json')
        st.subheader('Sensibilidade do corte de roubo e furto')
        resumo = obter_resumo(pasta,externo,versao,config_json,referencias,confirmacoes)
        corte = st.slider('Prioridade mínima para sinalizar análise',0,100,int(config['planos']['limiar_cobertura']))
        selecionados = resumo[ROUBO].ge(corte)
        st.metric('Unidades sinalizadas',int(selecionados.sum()))
        st.caption(f'{selecionados.mean():.1%} da base. Essa triagem isolada não substitui a comparação dos planos.')
        with st.expander('Dicionário original de dados'):
            st.dataframe(base.dicionario,hide_index=True,use_container_width=True)

    elif pagina == 'Exportar':
        st.write('Gere os dois templates oficiais com as colunas originais e uma trilha completa dos cálculos.')
        st.warning('Faixas são cenários para análise, não preços do seguro. Cobertura cibernética não será incluída como contratada.')
        chave = (pasta,externo,versao,config_json,referencias,confirmacoes)
        if st.button('Preparar exportação',type='primary'):
            with st.spinner('Gerando templates e auditoria…'):
                r,c,a = analisar_base(base,config)
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as z:
                    z.writestr('template_resultado_times.csv',csv_bytes(r))
                    z.writestr('template_coberturas_times.csv',csv_bytes(c))
                    z.writestr('auditoria.json',json.dumps(a,ensure_ascii=False,allow_nan=False))
                    z.writestr('config_regras.json',config_json)
                    z.writestr('fontes_sha256.json',json.dumps(base.hashes,indent=2))
                st.session_state.exportacao = (chave,csv_bytes(r),csv_bytes(c),buffer.getvalue(),len(r))
        pacote = st.session_state.get('exportacao')
        if pacote and pacote[0] == chave:
            st.success(f'{pacote[4]} estabelecimentos processados.')
            st.download_button('Baixar resultados',pacote[1],file_name='template_resultado_times.csv',mime='text/csv')
            st.download_button('Baixar coberturas',pacote[2],file_name='template_coberturas_times.csv',mime='text/csv')
            st.download_button('Baixar pacote com auditoria',pacote[3],file_name='resultado_datathon.zip',mime='application/zip')


if __name__ == '__main__':
    main()
