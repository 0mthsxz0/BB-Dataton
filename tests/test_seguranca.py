import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from seguranca import avaliar_seguranca, verificar_snapshot
from motor_pontuacao import MotorPontuacao, ROUBO
from territorio_ssp import construir_enriquecimento
from processamento import incorporar_ssp
from localizacao import aplicar_localizacao
from scripts.auditar_sinesp import auditar


def referencia(**extras):
    r = dict(codigo_ibge_municipio='5300108',uf_real='DF',seguranca_da_cidade_0_1=.5,
             confianca_seguranca_0_1=.55,periodo_seguranca='2025',granularidade_seguranca='MUNICIPIO',
             fonte_seguranca='https://fonte.exemplo/ssp',metodologia_seguranca='Roubo em comércio',
             fonte_denominador='Fonte sintética de estabelecimentos',ano_denominador='2025',
             sha256_arquivos='a'*64,roubo_comercio_total=10,estabelecimentos_referencia=100,
             taxa_por_mil_estabelecimentos=100,referencia_taxa_por_mil=100,indicador_disponivel='SIM',
             meses_observados_seguranca=12,cobertura_municipal_completa='SIM',integridade_seguranca='VERIFICADA')
    r['categoria_seguranca']='ROUBO_EM_COMERCIO'
    r.update(extras)
    return r


def test_zero_observado_e_diferente_de_dado_ausente():
    zero = referencia(roubo_comercio_total=0,taxa_por_mil_estabelecimentos=0,seguranca_da_cidade_0_1=1)
    assert avaliar_seguranca(zero,'2026-10-28')['utilizavel']
    sem = avaliar_seguranca(referencia(roubo_comercio_total=None),'2026-10-28')
    assert not sem['utilizavel']
    assert sem['status'] == 'INCONSISTENTE'


@pytest.mark.parametrize('alteracao,status',[
    ({'periodo_seguranca':'2021'},'DESATUALIZADO'),
    ({'periodo_seguranca':'2026'},'PERIODO_INVALIDO'),
    ({'periodo_seguranca':'2027'},'PERIODO_INVALIDO'),
    ({'periodo_seguranca':'2025-jan/set'},'PERIODO_INVALIDO'),
    ({'ano_denominador':'2024'},'COBERTURA_INSUFICIENTE'),
    ({'meses_observados_seguranca':11},'COBERTURA_INSUFICIENTE'),
    ({'cobertura_municipal_completa':'NAO'},'COBERTURA_INSUFICIENTE'),
    ({'fonte_denominador':''},'METADADOS_INSUFICIENTES'),
    ({'taxa_por_mil_estabelecimentos':101},'INCONSISTENTE'),
    ({'seguranca_da_cidade_0_1':.9},'INCONSISTENTE'),
    ({'roubo_comercio_total':1.5},'INCONSISTENTE'),
    ({'estabelecimentos_referencia':0},'INCONSISTENTE'),
    ({'integridade_seguranca':'SEM_MANIFESTO'},'INTEGRIDADE_NAO_VERIFICADA'),
    ({'sha256_arquivos':'hash-invalido'},'INCONSISTENTE'),
    ({'uf_real':'SP'},'LOCALIZACAO_INVALIDA'),
    ({'taxa_furto_domicilios':.1},'INCOMPATIVEL'),
    ({'categoria_seguranca':'ROUBO_VEICULO'},'INCOMPATIVEL'),
])
def test_dados_inadequados_nao_alimentam_a_nota(alteracao,status):
    r = referencia(**alteracao)
    qualidade = avaliar_seguranca(r,'2026-10-28')
    assert qualidade['status'] == status and not qualidade['utilizavel']
    s = MotorPontuacao(data_analise='2026-10-28').analisar_registro(r)[ROUBO]
    assert s['risco_evento_relativo'] == .5 and s['confianca_evento'] == 0
    assert s['probabilidade_sinistro'] is None


def test_validade_reproduzivel_e_calibracao_nao_inventada():
    r=referencia(periodo_seguranca='2024',ano_denominador='2024')
    assert avaliar_seguranca(r,'2026-12-31')['utilizavel']
    assert avaliar_seguranca(r,'2027-01-01')['status']=='DESATUALIZADO'
    assert avaliar_seguranca(r,'2026-10-28')['calibrado'] is False


def test_hash_modificado_rejeitado_antes_da_analise(tmp_path):
    arquivo=tmp_path/'seguranca_ssp.csv'
    df=pd.DataFrame([referencia()])
    df.to_csv(arquivo,index=False)
    arquivo.with_name(arquivo.name+'.manifesto.json').write_text(json.dumps({
        'arquivos':{arquivo.name:hashlib.sha256(arquivo.read_bytes()).hexdigest()}}),encoding='utf-8')
    assert verificar_snapshot(arquivo)=='VERIFICADA'
    arquivo.write_bytes(arquivo.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='Integridade'):
        incorporar_ssp(pd.DataFrame([{'codigo_ibge_municipio':'5300108'}]),arquivo)


def test_denominador_sem_fonte_ou_de_outro_ano_nao_gera_taxa():
    r=dict(uf='DF',codigo_ibge_municipio='5300108',regiao_administrativa='TOTAL',ano='2025',
           meses_observados=12,roubo_comercio_total=10,estabelecimentos=100,
           cobertura_municipal_completa='SIM',fonte='fonte-teste',sha256_arquivo='a'*64)
    for extras in ({},{'fonte_denominador':'teste','ano_denominador':'2024'}):
        df=construir_enriquecimento([dict(r,**extras)])
        assert df.iloc[0].indicador_disponivel=='NAO'
        assert df.iloc[0].roubo_comercio_total==10
        assert pd.isna(df.iloc[0].taxa_por_mil_estabelecimentos)


def test_municipio_e_uf_incompativeis_rejeitados():
    r=dict(uf='DF',codigo_ibge_municipio='3550308',ano='2025')
    with pytest.raises(ValueError,match='IBGE incompatível'):
        construir_enriquecimento([r])


def test_troca_de_cidade_limpa_simulacao_e_metadados(registro,tmp_path):
    r=dict(registro,**{k:v for k,v in referencia().items() if k not in registro})
    novo,_=aplicar_localizacao(r,{'codigo_ibge_municipio':'3550308','uf_real':'SP'},tmp_path)
    assert novo.get('fonte_denominador') is None
    assert novo.get('tipo_seguranca') is None
    assert not avaliar_seguranca(novo)['utilizavel']


def test_auditoria_sinesp_nao_converte_outro_crime_em_risco_empresarial(tmp_path):
    arquivo=tmp_path/'vde.xlsx'
    pd.DataFrame([dict(uf='DF',municipio='BRASILIA',evento='Roubo de veículo',
                       data_referencia='2025-01-01',abrangencia='Estadual')]).to_excel(arquivo,index=False)
    a=auditar(arquivo,'fonte-teste','2026-10-28T12:00:00-03:00')
    assert not a['uso_no_indice_empresarial']
    assert not a['categorias_comerciais_compativeis']
    assert a['meses_presentes_no_arquivo']==[1]
    assert a['sha256_original']==hashlib.sha256(arquivo.read_bytes()).hexdigest()
