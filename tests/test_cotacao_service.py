"""Contrato do formulário: regras reais, base sintética e rede isolada."""
import copy
import json

import pytest
import requests

import cotacao_service as service
from motor_pontuacao import ROUBO, VENDAVAL, EMPREGADOR, VIDROS
from processamento import carregar_base


@pytest.fixture
def payload():
    return {'activityId':'625','subactivityId':'R3.10','protection':'both','shopping':'no',
            'city':'Cidade de Teste','uf':'SP','contentsValue':100000,'equipmentValue':20000,
            'stockValue':10000,'glassValue':5000,'payroll':10000,'monthlyExpenses':20000,
            'monthlyRevenue':80000,'employees':5,
            'answers':{'securityControls':True,'portableGoods':True,'roofMaintained':True,
                       'exposedAssets':False,'hasEmployees':True,'hazardousWork':False,
                       'hasGlass':True,'glassExposed':False}}


@pytest.fixture
def analyze(monkeypatch):
    monkeypatch.setattr(service,'base_opcional',lambda:None)
    def local(city,uf):
        return {'codigo_ibge_municipio':'0000000','municipio_real':city,'uf_real':uf},[]
    return lambda p,base=None:service.analisar(p,base=base,municipio_fn=local)


def test_completo_reprodutivel_e_sem_dados_pessoais(analyze,payload):
    a=analyze(payload)
    b=analyze(dict(payload,name='Segredo',email='privado@example.com',phone='11999999999'))
    assert a==b
    assert len(a['indices'])==4
    assert len(a['recomendacao']['necessidades'])==10
    assert a['patrimonio']['bens_ponderados']==100000
    assert a['indices'][ROUBO]['valor_exposto_brl']==110000
    assert a['recomendacao']['comparacao'][-1]['aderencia_percentual']==pytest.approx(100)
    assert 'privado@example.com' not in json.dumps(b)


def test_cada_resposta_modifica_o_indice_correto(analyze,payload):
    baseline=analyze(payload)['indices']
    for key,code,value,direction in [
        ('securityControls',ROUBO,False,1),('portableGoods',ROUBO,False,-1),
        ('roofMaintained',VENDAVAL,False,1),('exposedAssets',VENDAVAL,True,1),
        ('hasEmployees',EMPREGADOR,False,-1),('hazardousWork',EMPREGADOR,True,1),
        ('hasGlass',VIDROS,False,-1),('glassExposed',VIDROS,True,1)]:
        p=copy.deepcopy(payload)
        p['answers'][key]=value
        if key=='hasEmployees':p['employees']=p['payroll']=0
        if key=='hasGlass':p['glassValue']=0
        result=analyze(p)['indices']
        assert direction*(result[code]['prioridade']-baseline[code]['prioridade'])>0,key
        for other in baseline:
            if other!=code:assert result[other]['prioridade']==baseline[other]['prioridade'],(key,other)


def test_campo_vazio_herda_e_zero_substitui_base(analyze,payload,pasta_csv):
    b=carregar_base(pasta_csv)
    p=dict(payload,empresaId='EMP_TESTE',imovelId='IMO_TESTE',contentsValue='',equipmentValue='',
           city='Município de teste',uf='XX')
    # Fixture has an intentionally invalid UF; use valid local values for the HTTP contract.
    b.estabelecimentos['uf_real']='SP'
    p['uf']='SP'
    result=analyze(p,b)
    assert result['patrimonio']['bens_ponderados']==50000
    assert result['patrimonio']['equipamentos_ponderados']==50000
    p.update(contentsValue=0,equipmentValue=0)
    assert analyze(p,b)['patrimonio']['bens_ponderados']==0


def test_escopo_imovel_e_conteudo(analyze,payload):
    p=dict(payload,buildingValue=400000)
    both=analyze(p)
    building=analyze(dict(p,protection='building'))
    contents=analyze(dict(p,protection='contents'))
    assert both['indices'][VENDAVAL]['valor_exposto_brl']==510000
    assert building['indices'][VENDAVAL]['valor_exposto_brl']==400000
    assert building['indices'][ROUBO]['valor_exposto_brl']==0
    assert building['indices'][ROUBO]['prioridade']==0
    assert contents['indices'][VENDAVAL]['valor_exposto_brl']==110000


@pytest.mark.parametrize('change',[
    {'subactivityId':'C1.10'}, {'activityId':'inventado'}, {'answers':{}},
    {'contentsValue':-1}, {'contentsValue':'NaN'}, {'equipmentValue':200000},
    {'employees':1.2}, {'uf':'ZZ'}, {'cnae':'625'}, {'units':0}, {'units':1.2},
])
def test_rejeita_entrada_invalida(analyze,payload,change):
    with pytest.raises(ValueError):analyze(dict(payload,**change))


def test_indisponibilidade_ibge_nao_inventa_indice(monkeypatch):
    def offline(*args,**kwargs):raise requests.ConnectionError('offline')
    monkeypatch.setattr(service.requests,'get',offline)
    local,notices=service.consultar_municipio('São Paulo','SP')
    assert local['codigo_ibge_municipio']=='' and notices


def test_resolve_codigo_real_ibge_por_nome_e_uf(monkeypatch):
    class Response:
        def raise_for_status(self):pass
        def json(self):return [{'id':3550308,'nome':'São Paulo'}]
    monkeypatch.setattr(service.requests,'get',lambda *args,**kwargs:Response())
    local,notices=service.consultar_municipio('Sao Paulo','SP')
    assert local['codigo_ibge_municipio']=='3550308' and not notices


def test_snapshot_fallback_exige_nome_e_uf_exatos(monkeypatch,tmp_path):
    refs=tmp_path/'refs'
    refs.mkdir()
    (refs/'seguranca_municipal.csv').write_text('codigo_ibge_municipio,municipio\n3550308,São Paulo - SP\n',encoding='utf-8')
    monkeypatch.setenv('BB_DATATHON_REFERENCIAS',str(refs))
    def offline(*args,**kwargs):raise requests.ConnectionError('offline')
    monkeypatch.setattr(service.requests,'get',offline)
    local,notices=service.consultar_municipio('Sao Paulo','SP')
    assert local['codigo_ibge_municipio']=='3550308' and notices
    wrong,_=service.consultar_municipio('Sao Paulo','RJ')
    assert wrong['codigo_ibge_municipio']==''


def test_ausencia_nao_significa_seguranca(analyze,payload):
    result=analyze(payload)
    assert result['indices'][VENDAVAL]['risco_evento_relativo']==.5
    assert result['indices'][VENDAVAL]['confianca_evento']==0
    assert all(not s['disponivel'] for s in result['fontes'])
    assert result['indices'][VENDAVAL]['prioridade_max']>result['indices'][VENDAVAL]['prioridade_min']


def test_contradicoes_rejeitadas(analyze,payload):
    for key in ('hasEmployees','hasGlass'):
        p=copy.deepcopy(payload)
        p['answers'][key]=False
        with pytest.raises(ValueError):analyze(p)


def test_vulnerabilidade_financeira_nao_rateia_receita_entre_filiais(analyze,payload):
    single=analyze(dict(payload,units=1))['indices'][ROUBO]
    multiple=analyze(dict(payload,units=3))['indices'][ROUBO]
    assert single['vulnerabilidade']==.25
    assert multiple['vulnerabilidade']==.5
    assert single['prioridade']<multiple['prioridade']


def test_cnae_alterado_limpa_referencia_ocupacional_anterior(analyze,payload,pasta_csv):
    b=carregar_base(pasta_csv)
    b.estabelecimentos['uf_real']='SP'
    b.estabelecimentos['grau_risco_nr4']=4
    b.estabelecimentos['fonte_nr4']='Fonte antiga'
    result=analyze(dict(payload,empresaId='EMP_TESTE',imovelId='IMO_TESTE',cnae='9999999',
                        city='Município de teste',uf='SP'),b)
    assert result['indices'][EMPREGADOR]['referencia_evento']['grau_risco_nr4'] is None
    assert result['fontes'][2]['fonte'] is None
    assert result['fontes'][2]['disponivel'] is False


def test_ssp_sem_confianca_nao_aparece_como_indicador_disponivel(monkeypatch,analyze,payload):
    def local(record,localizacao):
        return dict(record,**localizacao,seguranca_da_cidade_0_1=.5,confianca_seguranca_0_1=0,
                    indicador_disponivel='NAO',fonte_seguranca='SSP teste'),[]
    monkeypatch.setattr(service,'aplicar_localizacao',local)
    result=analyze(payload)
    assert result['fontes'][0]['disponivel'] is False


def test_cadastro_recomenda_sem_questionario_ou_atividade_inventados(pasta_csv):
    from motor_pontuacao import MotorPontuacao
    from recomendador import recomendar_plano
    b=carregar_base(pasta_csv)
    before=b.registro('EMP_TESTE','IMO_TESTE')
    result=service.analisar_cadastro({'empresaId':'EMP_TESTE','imovelId':'IMO_TESTE'},base=b)
    expected_indices=MotorPontuacao().analisar_registro(before)
    expected_plan=recomendar_plano(expected_indices,b.catalogo,registro=before)
    assert result['preliminar'] is True
    assert result['respostas'] is None
    assert result['atividade']['id'] is None
    for code, expected in expected_indices.items():
        assert all(result['indices'][code][key]==value for key,value in expected.items())
        assert result['indices'][code]['leitura_contextual']
    assert result['recomendacao']['plano_recomendado']==expected_plan['plano_recomendado']
    assert result['dadosCadastrais']['bens_ponderados']==50000
    assert b.registro('EMP_TESTE','IMO_TESTE')==before
    assert len(result['recomendacao']['necessidades'])==10
    for plan in result['recomendacao']['comparacao']:
        covered=sum(n['prioridade']*n['peso'] for code,n in result['recomendacao']['necessidades'].items() if code in plan['coberturas'])
        assert plan['pontos_atendidos']==pytest.approx(covered)
        assert plan['aderencia_percentual']==pytest.approx(covered/plan['pontos_totais']*100)


def test_cadastro_nao_aceita_vinculo_de_outra_empresa(pasta_csv):
    b=carregar_base(pasta_csv)
    with pytest.raises(ValueError):
        service.analisar_cadastro({'empresaId':'OUTRA_EMPRESA','imovelId':'IMO_TESTE'},base=b)


@pytest.mark.parametrize('payload',[None,{}, {'empresaId':[], 'imovelId':'IMO_TESTE'}, {'empresaId':'EMP_TESTE'}])
def test_cadastro_valida_identificadores_antes_de_carregar_dados(payload):
    with pytest.raises(ValueError):service.analisar_cadastro(payload)


@pytest.mark.parametrize('changes', [
    {'coverageAdjustments':{'exclude':['PROTECAO_CIBERNETICA_AVALIAR']}},
    {'coverageAdjustments':{'include':['QUEBRA_DE_VIDROS'],'exclude':['QUEBRA_DE_VIDROS']}},
    {'selectedPlan':'ESSENCIAL','coverageAdjustments':{'include':['QUEBRA_DE_VIDROS']}},
    {'operations':{'delivery':'yes'}},
    {'operations':{'shoppingControls':True}},
    {'selectedPlan':'PRATICO','indispensable':['RESPONSABILIDADE_CIVIL_EMPREGADOR']},
    {'optionalCovers':['INVENTADA']}, {'termYears':1.5}, {'termYears':6}, {'termYears':True}, {'priority':'inventada'}])
def test_rejeita_personalizacao_inconsistente(analyze,payload,changes):
    with pytest.raises(ValueError): analyze(dict(payload,**changes))


def test_pacote_personalizado_e_operacao_confirmada(analyze,payload):
    r=analyze(dict(payload,selectedPlan='PRATICO',operations={'refrigeration':True},
        optionalCovers=['DETERIORACAO_MERCADORIAS_FRIGORIFICADAS'],
        coverageAdjustments={'include':['QUEBRA_DE_VIDROS'],'exclude':['VENDAVAL_EVENTOS_CORRELATOS']},
        priority='continuidade',termYears=3))
    p=r['personalizacao']['pacote']
    assert p['plano']=='PRATICO' and p['vigencia_anos']==3
    assert 'QUEBRA_DE_VIDROS' in p['coberturas'] and 'VENDAVAL_EVENTOS_CORRELATOS' not in p['coberturas']
    assert len(p['obrigatorias'])==6 and set(p['obrigatorias'])<=set(p['coberturas'])
    assert p['adicionais_condicionais']==['DETERIORACAO_MERCADORIAS_FRIGORIFICADAS']
    assert r['recomendacao']['necessidades']['DESPESAS_FIXAS']['peso']==1.5


@pytest.mark.parametrize('changes',[
    {'selectedPlan':'ESSENCIAL','operations':{'delivery':True},'optionalCovers':['DELIVERY']},
    {'selectedPlan':'TOTAL','operations':{'delivery':False},'optionalCovers':['DELIVERY']},
    {'selectedPlan':'TOTAL','optionalCovers':['DELIVERY']}])
def test_nao_inventa_compatibilidade_de_adicionais(analyze,payload,changes):
    with pytest.raises(ValueError): analyze(dict(payload,**changes))


def test_triagem_impede_indicacao_comparacao_permanece_auditavel(analyze,payload):
    r=analyze(dict(payload,propertyStatus='EM_OBRA'))
    assert r['recomendacao']['indicacao_bloqueada']
    assert r['personalizacao']['triagem']['bloqueado']
    assert len(r['recomendacao']['comparacao'])==3


def test_rastreabilidade_declara_valores_substituidos_sem_reutilizar_cadastro(analyze,payload,pasta_csv):
    base=carregar_base(pasta_csv)
    r=analyze(dict(payload,empresaId='EMP_TESTE',imovelId='IMO_TESTE'),base)
    e=next(x for x in r['dimensionamento'][ROUBO]['evidencias'] if x['campo']=='bens_ponderados')
    assert e['valor']==100000 and e['estado']=='DECLARADO' and e['arquivo'] is None
    assert not r['rastreabilidade']['bens_cadastrais_utilizados']
    assert r['rastreabilidade']['bens'][0]['valor_ponderado']==50000
    assert r['patrimonio']['bens_ponderados']==100000
    total=next(x for x in r['dimensionamento'][ROUBO]['evidencias'] if x['campo']=='bens_total_referencia')
    assert total['valor']==100000 and total['estado']=='DECLARADO' and total['arquivo'] is None
    pico=next(x for x in r['dimensionamento'][ROUBO]['evidencias'] if x['campo']=='estoque_pico_estimado')
    assert pico['valor']==10000 and pico['estado']=='DECLARADO' and pico['arquivo'] is None
    assert r['indices'][ROUBO]['respostas_utilizadas']['securityControls'] is True
    assert 'R$ 100.000,00' in r['indices'][ROUBO]['leitura_contextual']
    assert r['indices'][VIDROS]['referencia_publica'] is None

def test_quantidade_vidros_nao_inventa_valor_de_reposicao(analyze,payload):
    payload.pop('glassValue')
    baseline=analyze(payload)
    r=analyze(dict(payload,glassCount='8'))
    assert r['vidrosDeclarados']['quantidade']==8
    assert r['vidrosDeclarados']['valorReposicaoPendente']
    assert r['dimensionamento'][VIDROS]['faixa_valor_min'] is None
    assert r['dimensionamento'][VIDROS]['faixa_valor_max'] is None
    assert r['indices'][VIDROS]==baseline['indices'][VIDROS]

@pytest.mark.parametrize('q',[-1,1.5,True,1000001,'abc'])
def test_quantidade_vidros_invalida(analyze,payload,q):
    with pytest.raises(ValueError,match='quantidade inteira'):
        analyze(dict(payload,glassCount=q))

@pytest.mark.parametrize('q,presente',[(0,True),(3,False)])
def test_quantidade_vidros_contraditoria(analyze,payload,q,presente):
    p=copy.deepcopy(payload);p['glassCount']=q;p['answers']['hasGlass']=presente
    with pytest.raises(ValueError,match='não combina'):
        analyze(p)

def test_zero_vidros_significa_ausencia_confirmada(analyze,payload):
    p=copy.deepcopy(payload);p.update(glassCount=0,glassValue=0)
    p['answers'].update(hasGlass=False,glassExposed=False)
    r=analyze(p)
    assert r['vidrosDeclarados']['quantidade']==0
    assert r['indices'][VIDROS]['prioridade']==0
