import json

from cotacao_service import analisar_cadastro
from processamento import carregar_base
from motor_pontuacao import ROUBO, VENDAVAL, EMPREGADOR, VIDROS


def test_bens_de_origem_batem_com_agregado_sem_outra_unidade(pasta_csv):
    base=carregar_base(pasta_csv)
    r=analisar_cadastro({'empresaId':'EMP_TESTE','imovelId':'IMO_TESTE'},base)
    trace=r['rastreabilidade']
    assert trace['vinculo']=={'empresa_id':'EMP_TESTE','imovel_id':'IMO_TESTE'}
    assert len(trace['bens'])==1
    assert trace['bens'][0]['bem_id']=='BEM_1'
    assert trace['bens'][0]['valor_cadastrado']==100000
    assert trace['bens'][0]['probabilidade_vinculo']==.5
    assert trace['bens'][0]['valor_ponderado']==50000
    assert sum(b['valor_ponderado'] for b in trace['bens'])==r['patrimonio']['bens_ponderados']
    estoque=next(e for e in r['dimensionamento'][ROUBO]['evidencias'] if e['campo']=='estoque_medio_estimado')
    assert estoque['valor']==10000  # A filial tem 100000, que não pode vazar nesta conta.
    assert estoque['arquivo']=='sinais_financeiros_operacionais.csv'
    assert estoque['sha256']==base.hashes['sinais_financeiros_operacionais.csv']
    bens=next(e for e in r['dimensionamento'][ROUBO]['evidencias'] if e['campo']=='bens_ponderados')
    assert bens['campos_origem']==['valor_cadastrado','probabilidade_bem_no_imovel_referencia']
    fonte=bens['fontes_originais'][0]
    assert fonte['linha_tabela']==2 and fonte['registro']=='BEM_1'
    assert {c['campo']:c['valor_original'] for c in fonte['celulas']}=={
        'valor_cadastrado':'100000','probabilidade_bem_no_imovel_referencia':'0.5'}
    assert bens['fonte_utilizada']
    assert 'vínculo' in bens['significado']
    assert 'Inventário' in bens['confirmacao']['onde_encontrar']
    assert estoque['fontes_originais'][0]['celulas'][0]['valor_original']=='10000'
    assert r['respostas'] is None
    assert all(v is None for v in r['indices'][ROUBO]['respostas_utilizadas'].values())
    json.dumps(r,allow_nan=False)


def test_celulas_preservam_grafia_e_isolam_unidade_e_categoria(pasta_csv):
    import pandas as pd
    path=pasta_csv/'bens_cadastrados.csv'
    bens=pd.read_csv(path,dtype=str,keep_default_na=False)
    bens.loc[0,'probabilidade_bem_no_imovel_referencia']='0.5000'
    bens=pd.concat([bens,pd.DataFrame([
        dict(bens.iloc[0],bem_id='BEM_FILIAL',imovel_id_referencia='IMO_FILIAL',valor_cadastrado='999999'),
        dict(bens.iloc[0],bem_id='MESA',tipo_bem='MOBILIARIO',valor_cadastrado='2000')])],ignore_index=True)
    bens.to_csv(path,index=False)
    r=analisar_cadastro({'empresaId':'EMP_TESTE','imovelId':'IMO_TESTE'},carregar_base(pasta_csv))
    evidencia=next(e for e in r['dimensionamento']['DANOS_ELETRICOS']['evidencias'] if e['campo']=='equipamentos_ponderados')
    assert len(evidencia['fontes_originais'])==1
    fonte=evidencia['fontes_originais'][0]
    assert fonte['registro']=='BEM_1'
    assert fonte['celulas'][1]['valor_original']=='0.5000'
    assert all('999999' not in json.dumps(e['fontes_originais']) for e in r['dimensionamento'][ROUBO]['evidencias'])
    assert {x['registro'] for x in r['dimensionamento'][ROUBO]['evidencias'][0]['fontes_originais']}=={'BEM_1','MESA'}


def test_ausente_expoe_celula_invalida_e_orienta_como_obter_o_dado(pasta_csv):
    import pandas as pd
    path=pasta_csv/'sinais_financeiros_operacionais.csv'
    sinais=pd.read_csv(path,dtype=str,keep_default_na=False)
    sinais.loc[0,'estoque_medio_estimado']='NAO_DISPONIVEL'
    sinais.to_csv(path,index=False)
    r=analisar_cadastro({'empresaId':'EMP_TESTE','imovelId':'IMO_TESTE'},carregar_base(pasta_csv))
    e=next(e for e in r['dimensionamento'][ROUBO]['evidencias'] if e['campo']=='estoque_medio_estimado')
    assert e['valor'] is None and not e['fonte_utilizada']
    assert e['fontes_originais'][0]['celulas'][0]['valor_original']=='NAO_DISPONIVEL'
    assert e['estado']=='AUSENTE'
    assert 'não é válido' in e['confirmacao']['motivo']
    assert 'Controle de estoque' in e['confirmacao']['onde_encontrar']
    predio=next(e for e in r['dimensionamento'][VENDAVAL]['evidencias'] if e['campo']=='valor_predio_reposicao_brl')
    assert predio['fontes_originais']==[]
    assert 'construtora' in predio['confirmacao']['onde_encontrar']


def test_contagem_de_unidades_expoe_linhas_sem_outros_campos(pasta_csv):
    r=analisar_cadastro({'empresaId':'EMP_TESTE','imovelId':'IMO_TESTE'},carregar_base(pasta_csv))
    e=next(e for e in r['indices'][ROUBO]['evidencias'] if e['campo']=='quantidade_unidades')
    assert e['valor']==2 and len(e['fontes_originais'])==2
    assert [x['linha_tabela'] for x in e['fontes_originais']]==[2,3]
    assert all({c['campo'] for c in x['celulas']}=={'empresa_id','imovel_id'} for x in e['fontes_originais'])


def test_fontes_publicas_mostram_valores_periodos_e_natureza_sem_api_inventada(pasta_csv):
    base=carregar_base(pasta_csv)
    valores={'taxa_furto_domicilios':.04,'taxa_roubo_domicilios':.02,'exposicao_bruta':.03,
        'seguranca_da_cidade_0_1':.7,'confianca_seguranca_0_1':.35,'fonte_seguranca':'https://sidra.ibge.gov.br/tabela/8510','periodo_seguranca':'2021',
        'grau_risco_nr4':2,'descricao_nr4':'Classe sintética','classe_cnae':'00000','pagina':8,'fonte_nr4':'https://www.gov.br/documento-fixture.pdf',
        'versao_nr4':'Edição de teste','frequencia_rajada_forte':.123,'fonte_clima':'https://open-meteo.com/en/docs/historical-weather-api',
        'exposicao_climatica_0_1':.6,'confianca_clima_0_1':.55,'periodo_clima':'1996/2025'}
    for c,v in valores.items():base.estabelecimentos[c]=v
    r=analisar_cadastro({'empresaId':'EMP_TESTE','imovelId':'IMO_TESTE'},base)
    p=r['indices'][ROUBO]['referencia_publica']
    assert p['dados']['taxa_furto_domicilios']==.04 and p['periodo']=='2021'
    assert p['consulta_ao_vivo'] is False and not p['disponivel']
    assert not p['qualidade']['utilizavel']  # Valor histórico visível, sem usá-lo como risco empresarial.
    assert r['indices'][VENDAVAL]['referencia_publica']['dados']['frequencia_rajada_forte']==.123
    assert r['indices'][EMPREGADOR]['referencia_publica']['dados']['grau_risco_nr4']==2
    assert 'documento oficial' in r['indices'][EMPREGADOR]['referencia_publica']['modo_acesso']
    assert r['indices'][VIDROS]['referencia_publica'] is None
    assert 'Não existe uma API' in r['indices'][VIDROS]['explicacao_contextual']


def test_ssp_nao_apresenta_taxas_domiciliares_como_fonte_atual(pasta_csv):
    base=carregar_base(pasta_csv)
    for c,v in {'roubo_comercio_total':12,'estabelecimentos_referencia':1000,'taxa_por_mil_estabelecimentos':12,
                'taxa_furto_domicilios':.99,'fonte_seguranca':'https://www.ssp.df.gov.br/fixture','periodo_seguranca':'2025'}.items():
        base.estabelecimentos[c]=v
    r=analisar_cadastro({'empresaId':'EMP_TESTE','imovelId':'IMO_TESTE'},base)
    p=r['indices'][ROUBO]['referencia_publica']
    assert p['arquivo']=='seguranca_ssp.csv'
    assert p['dados']['roubo_comercio_total']==12
    assert 'taxa_furto_domicilios' not in p['dados']


def test_sem_referencia_nao_inventa_disponibilidade(pasta_csv):
    base=carregar_base(pasta_csv)
    r=analisar_cadastro({'empresaId':'EMP_TESTE','imovelId':'IMO_TESTE'},base)
    for c in (ROUBO,VENDAVAL,EMPREGADOR):
        assert not r['indices'][c]['referencia_publica']['disponivel']
        assert 'ausente' in r['indices'][c]['referencia_publica']['condicao']


def test_ponderacao_invalida_nao_e_apresentada_como_valor_utilizado(pasta_csv):
    import pandas as pd
    path=pasta_csv/'bens_cadastrados.csv'
    bens=pd.read_csv(path)
    bens['probabilidade_bem_no_imovel_referencia']=1.5
    bens.to_csv(path,index=False)
    base=carregar_base(pasta_csv)
    r=analisar_cadastro({'empresaId':'EMP_TESTE','imovelId':'IMO_TESTE'},base)
    assert r['rastreabilidade']['bens'][0]['valor_ponderado'] is None
    assert not r['rastreabilidade']['bens_cadastrais_utilizados']
    e=next(e for e in r['dimensionamento'][ROUBO]['evidencias'] if e['campo']=='bens_ponderados')
    assert 'não entra na soma ponderada' in e['fontes_originais'][0]['observacao']
