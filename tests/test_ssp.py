from unittest.mock import Mock
import pandas as pd
import pytest

from territorio_ssp import _numero, ler_balanco_ssp, construir_enriquecimento, construir_de_manifesto, MESES
from processamento import carregar_base, incorporar_ssp, incorporar_territorio
from localizacao import aplicar_localizacao
from motor_pontuacao import MotorPontuacao, ROUBO


def registro_ssp(ibge='5300108',regiao='A',total=100,estabelecimentos=100,**extras):
    return dict({'uf':'DF','regiao_administrativa':regiao,'ano':'2025',
        'codigo_ibge_municipio':ibge,'roubo_comercio_total':total,
        'estabelecimentos':estabelecimentos,'meses_observados':12,
        'cobertura_municipal_completa':'SIM','fonte':'https://fonte.exemplo/planilha',
        'sha256_arquivo':'a'*64},**extras)


def planilha(caminho,ausente=False,total=12):
    pd.DataFrame([['Título institucional']+[None]*13,
        ['NATUREZA DO CRIME',*MESES,'TOTAL'],
        ['ROUBO EM COMÉRCIO',*([1.]*11+[None if ausente else 1.]),total]]).to_excel(caminho,index=False,header=False)


@pytest.mark.parametrize('valor,esperado',[(12.,12),(12,12),('12,0',12),('1.234,00',1234),('12.0',12),('',None),(None,None),(float('nan'),None)])
def test_numeros_excel_sem_mudar_ordem_grandeza(valor,esperado):
    assert _numero(valor)==esperado


def test_planilha_real_xlsx_e_ausencia(tmp_path):
    caminho=tmp_path/'balanco.xlsx'
    planilha(caminho)
    kwargs=dict(uf='DF',regiao='TOTAL',ano=2025,codigo_ibge_municipio='5300108',
                fonte='https://fonte.exemplo',estabelecimentos='100',cobertura_municipal_completa='SIM')
    r=ler_balanco_ssp(caminho,**kwargs)
    assert r['roubo_comercio_total']==12
    assert r['meses_observados']==12
    assert len(r['sha256_arquivo'])==64
    planilha(caminho,ausente=True)
    r=ler_balanco_ssp(caminho,**kwargs)
    assert r['roubo_comercio_total'] is None
    s=construir_enriquecimento([r]).iloc[0]
    assert s['indicador_disponivel']=='NAO'
    assert pd.isna(s['roubo_comercio_total'])
    assert s['confianca_seguranca_0_1']==0
    planilha(caminho,total=13)
    with pytest.raises(ValueError,match='diverge'):
        ler_balanco_ssp(caminho,**kwargs)


def test_taxa_consolidada_e_referencia_estavel():
    linhas=[registro_ssp(regiao='A',total=100,estabelecimentos=100),
            registro_ssp(regiao='B',total=100,estabelecimentos=10000)]
    s=construir_enriquecimento(linhas).iloc[0]
    assert s['taxa_por_mil_estabelecimentos']==pytest.approx(200/10100*1000)
    assert s['confianca_seguranca_0_1']>0  # Um município basta quando a escala é fixa.
    outras=linhas+[registro_ssp(ibge='3550308',regiao='C',total=20000)]
    t=construir_enriquecimento(outras).set_index('codigo_ibge_municipio').loc['5300108']
    assert s['seguranca_da_cidade_0_1']==t['seguranca_da_cidade_0_1']


def test_ausente_nao_vira_zero_e_denominador_nao_se_mistura():
    a=registro_ssp(total=None)
    b=registro_ssp(ibge='3550308',estabelecimentos=None)
    c=registro_ssp(ibge='3304557',total=0)
    r=construir_enriquecimento([a,b,c]).set_index('codigo_ibge_municipio')
    assert pd.isna(r.loc['5300108','roubo_comercio_total'])
    assert r.loc['5300108','indicador_disponivel']=='NAO'
    assert r.loc['3550308','indicador_disponivel']=='NAO'
    assert r.loc['3304557','indicador_disponivel']=='SIM'
    assert r.loc['3304557','seguranca_da_cidade_0_1']==1


def test_anos_parciais_duplicados_e_sobreposicao_rejeitados():
    with pytest.raises(ValueError,match='períodos'):
        construir_enriquecimento([registro_ssp(),registro_ssp(regiao='B',ano='2024')])
    r=construir_enriquecimento([registro_ssp(),registro_ssp(regiao='B',ano='2024')],ano_referencia='2025')
    assert r.periodo_seguranca.eq('2025').all()
    with pytest.raises(ValueError,match='completa'):
        construir_enriquecimento([registro_ssp(cobertura_municipal_completa='NAO')])
    with pytest.raises(ValueError,match='duplicada'):
        construir_enriquecimento([registro_ssp(),registro_ssp()])
    with pytest.raises(ValueError,match='duplica'):
        construir_enriquecimento([registro_ssp(regiao='TOTAL'),registro_ssp(regiao='A')])


def test_ssp_na_base_no_motor_e_no_cep(pasta_csv,tmp_path,registro):
    referencias=tmp_path/'referencias'
    referencias.mkdir()
    ssp=construir_enriquecimento([registro_ssp(ibge='0000000')])
    caminho=referencias/'seguranca_ssp.csv'
    ssp.to_csv(caminho,index=False)
    base=carregar_base(pasta_csv,referencias=referencias)
    r=base.registro('EMP_TESTE','IMO_TESTE')
    s=MotorPontuacao(base).analisar_registro(r)[ROUBO]
    assert s['referencia_evento']['roubo_comercio_total']=='100.0'
    assert s['risco_evento_relativo']==pytest.approx(1000/1100,abs=1e-6)
    assert str(caminho.resolve()) in base.hashes
    local={'codigo_ibge_municipio':'0000000','municipio_real':'Teste','uf_real':'DF'}
    novo,avisos=aplicar_localizacao(registro,local,referencias)
    assert novo['sha256_arquivos']=='a'*64
    assert MotorPontuacao().analisar_registro(novo)[ROUBO]['risco_evento_relativo']==s['risco_evento_relativo']
    assert novo['bens_ponderados']==registro['bens_ponderados']
    assert len(avisos)==1  # Clima não está neste arquivo.


def test_ssp_nao_altera_clima_nem_cidade_fora_da_cobertura(tmp_path):
    caminho=tmp_path/'ssp.csv'
    construir_enriquecimento([registro_ssp()]).to_csv(caminho,index=False)
    dados=pd.DataFrame([{'codigo_ibge_municipio':'5300108','seguranca_da_cidade_0_1':.9,
        'taxa_roubo_domicilios':.1,'exposicao_climatica_0_1':.3},
        {'codigo_ibge_municipio':'3550308','seguranca_da_cidade_0_1':.8,
         'taxa_roubo_domicilios':.2,'exposicao_climatica_0_1':.5}])
    novo=incorporar_ssp(dados,caminho)
    assert novo.exposicao_climatica_0_1.tolist()==[.3,.5]
    assert novo.iloc[1].seguranca_da_cidade_0_1==.8
    assert pd.isna(novo.iloc[0].taxa_roubo_domicilios)


def test_override_legado_nao_carrega_atribuicao_ssp_antiga(tmp_path):
    ssp=tmp_path/'ssp.csv'
    construir_enriquecimento([registro_ssp()]).to_csv(ssp,index=False)
    dados=incorporar_ssp(pd.DataFrame([{'codigo_ibge_municipio':'5300108'}]),ssp)
    externo=tmp_path/'externo.csv'
    pd.DataFrame([{'codigo_ibge_municipio':'5300108','seguranca_da_cidade_0_1':.8,
        'fonte':'Outra fonte documentada','ano_referencia':'2024','granularidade':'MUNICIPIO',
        'metodologia':'Outra metodologia','confianca_territorial_0_1':.4}]).to_csv(externo,index=False)
    novo=incorporar_territorio(dados,externo)
    assert novo.iloc[0].fonte_seguranca=='Outra fonte documentada'
    assert 'roubo_comercio_total' not in novo
    assert 'sha256_arquivos' not in novo


def test_download_cache_e_atualizacao_deliberada(tmp_path,monkeypatch):
    arquivo=tmp_path/'original.xlsx'
    planilha(arquivo)
    get=Mock(return_value=Mock(content=arquivo.read_bytes()))
    monkeypatch.setattr('territorio_ssp.requests.get',get)
    manifesto=tmp_path/'manifesto.csv'
    pd.DataFrame([dict(arquivo='',url='https://fonte.exemplo/arquivo.xlsx',uf='DF',regiao='TOTAL',
        ano='2025',codigo_ibge_municipio='5300108',estabelecimentos='100',cobertura_municipal_completa='SIM')]).to_csv(manifesto,index=False)
    destino=tmp_path/'refs'/'seguranca_ssp.csv'
    construir_de_manifesto(manifesto,destino)
    construir_de_manifesto(manifesto,destino)
    assert get.call_count==1
    r=construir_de_manifesto(manifesto,destino,atualizar=True)
    assert get.call_count==2
    assert r.indicador_disponivel.eq('SIM').all()
    assert r.fonte_seguranca.eq('https://fonte.exemplo/arquivo.xlsx').all()


def test_pasta_local_apenas_ssp_conserva_referencias_distribuidas(tmp_path,monkeypatch):
    import processamento
    from processamento import caminho_referencia
    monkeypatch.setattr(processamento,'__file__',str(tmp_path/'processamento.py'))
    local=tmp_path/'data'/'referencias'
    local.mkdir(parents=True)
    publica=tmp_path/'references'
    publica.mkdir()
    for nome in ['seguranca_municipal.csv','clima_municipal.csv','nr4_cnae.csv']:
        (publica/nome).write_text('snapshot',encoding='utf-8')
        assert caminho_referencia(nome,local)==publica/nome
    (local/'clima_municipal.csv').write_text('local',encoding='utf-8')
    assert caminho_referencia('clima_municipal.csv',local)==local/'clima_municipal.csv'
    # Pastas personalizadas explicitamente vazias continuam desconhecidas.
    personalizada=tmp_path/'personalizada'
    assert caminho_referencia('nr4_cnae.csv',personalizada)==personalizada/'nr4_cnae.csv'
