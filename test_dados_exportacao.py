import json
import pandas as pd
import pytest
from processamento import carregar_base
from exportacao import analisar_base, exportar
from motor_pontuacao import MotorPontuacao, ROUBO, INCENDIO, CIBER, EMPREGADOR
from recomendador import recomendar_plano, verificar_elegibilidade


def test_duas_unidades_independentes_e_ponderacao_unica(pasta_csv):
    base = carregar_base(pasta_csv)
    assert len(base.estabelecimentos) == 2
    r = base.registro('EMP_TESTE','IMO_TESTE')
    assert r['bens_ponderados'] == 50000
    assert r['faturamento_mensal'] == '100000'
    assert r['quantidade_unidades'] == 2
    motor = MotorPontuacao(base)
    assert motor.calcular_pontuacoes('EMP_TESTE','IMO_TESTE')[ROUBO]['prioridade'] != motor.calcular_pontuacoes('EMP_TESTE','IMO_FILIAL')[ROUBO]['prioridade']


def test_bem_duplicado_identico_nao_duplica_patrimonio(pasta_csv):
    p = pasta_csv/'bens_cadastrados.csv'
    b = pd.read_csv(p)
    pd.concat([b,b]).to_csv(p,index=False)
    assert carregar_base(pasta_csv).registro('EMP_TESTE','IMO_TESTE')['bens_ponderados'] == 50000


def test_bem_duplicado_conflitante_rejeitado(pasta_csv):
    p = pasta_csv/'bens_cadastrados.csv'
    b = pd.read_csv(p)
    outro = b.copy(); outro['valor_cadastrado'] = 999
    pd.concat([b,outro]).to_csv(p,index=False)
    with pytest.raises(ValueError,match='duplicada'):
        carregar_base(pasta_csv)


def test_chave_financeira_duplicada_rejeitada(pasta_csv):
    p = pasta_csv/'sinais_financeiros_operacionais.csv'
    b = pd.read_csv(p);pd.concat([b,b]).to_csv(p,index=False)
    with pytest.raises(ValueError,match='duplicada'):
        carregar_base(pasta_csv)


def test_probabilidade_localizacao_invalida_nao_vira_zero_risco(pasta_csv):
    p=pasta_csv/'bens_cadastrados.csv'
    b=pd.read_csv(p);b['probabilidade_bem_no_imovel_referencia']=1.5;b.to_csv(p,index=False)
    r=carregar_base(pasta_csv).registro('EMP_TESTE','IMO_TESTE')
    assert r['bens_ponderados'] is None
    assert r['bens_total_referencia']==100000
    assert r['confianca_bens']==0


def test_exportacao_esquema_completo_e_reprodutivel(pasta_csv,tmp_path):
    base=carregar_base(pasta_csv)
    r,c,a=analisar_base(base)
    assert list(r)==base.templates['template_resultado_times']
    assert list(c)==base.templates['template_coberturas_times']
    assert len(r)==2 and not r.duplicated(['empresa_id','imovel_id']).any()
    for linha in r.to_dict('records'):
        cs=c.loc[c.imovel_id.eq(linha['imovel_id'])]
        assert set(cs.cobertura)==set(linha['coberturas_recomendadas'].split('|'))
        assert CIBER not in set(cs.cobertura)
        assert cs.justificativa.str.len().gt(0).all()
    destino=tmp_path/'saida'
    exportar(base,destino=destino)
    antes=(destino/'template_resultado_times.csv').read_bytes()
    exportar(base,destino=destino)
    assert antes==(destino/'template_resultado_times.csv').read_bytes()
    assert json.loads((destino/'manifesto.json').read_text(encoding='utf-8'))['estabelecimentos']==2


def notas_controladas(registro):
    pontos=MotorPontuacao().analisar_registro(registro)
    for s in pontos.values():
        s.update(prioridade=10,prioridade_min=10,prioridade_max=10)
    return pontos


def test_cobertura_comum_alta_nao_provoca_upgrade(registro,catalogo):
    p=notas_controladas(registro);p[INCENDIO].update(prioridade=100,prioridade_min=100,prioridade_max=100)
    r=recomendar_plano(p,catalogo,registro=registro)
    assert r['plano_recomendado']=='ESSENCIAL'
    assert all(x['analise_preco']=='PENDENTE' for x in r['comparacao'])


def test_prioridade_roubo_justifica_pratico(registro,catalogo):
    p=notas_controladas(registro);p[ROUBO].update(prioridade=90,prioridade_min=90,prioridade_max=90)
    assert recomendar_plano(p,catalogo)['plano_recomendado']=='PRATICO'


def test_empregador_relevante_justifica_total(registro,catalogo):
    p=notas_controladas(registro);p[EMPREGADOR].update(prioridade=90,prioridade_min=90,prioridade_max=90)
    assert recomendar_plano(p,catalogo)['plano_recomendado']=='TOTAL'


def test_elegibilidade_nao_e_inventada(registro,config):
    e=verificar_elegibilidade(dict(registro,situacao_imovel_cadastral='EM_OBRA'),config)
    assert e['elegivel']=='PENDENTE'
    assert any('obra' in p for p in e['motivos'])


def test_territorio_documentado_por_codigo_ibge(pasta_csv,tmp_path):
    externo=tmp_path/'externo.csv'
    pd.DataFrame([{'codigo_ibge_municipio':'0000000','seguranca_da_cidade_0_1':.9,
        'fonte':'Fixture explícita','ano_referencia':'2021','granularidade':'MUNICIPIO',
        'metodologia':'Teste de cruzamento','confianca_territorial_0_1':.5}]).to_csv(externo,index=False)
    base=carregar_base(pasta_csv,externo)
    assert len(base.estabelecimentos)==2
    assert float(base.registro('EMP_TESTE','IMO_TESTE')['seguranca_da_cidade_0_1'])==.9
    assert 'enriquecimento_territorial.csv' in base.hashes
    b=pd.read_csv(externo,dtype=str);b['granularidade']='BAIRRO';b.to_csv(externo,index=False)
    with pytest.raises(ValueError,match='municipal'):
        carregar_base(pasta_csv,externo)
