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
    assert r['respostas'] is None
    assert all(v is None for v in r['indices'][ROUBO]['respostas_utilizadas'].values())
    json.dumps(r,allow_nan=False)


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
