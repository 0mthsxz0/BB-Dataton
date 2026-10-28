"""Dados sintéticos mínimos exclusivos para testes; não são recomendações reais."""
import csv
from pathlib import Path
import pandas as pd
import pytest
from motor_pontuacao import carregar_config


@pytest.fixture(autouse=True)
def referencias_isoladas(tmp_path,monkeypatch):
    monkeypatch.setenv('BB_DATATHON_REFERENCIAS',str(tmp_path/'sem_referencias'))


@pytest.fixture
def config():
    return carregar_config()


@pytest.fixture
def registro():
    return {
        'empresa_id':'EMP_TESTE', 'imovel_id':'IMO_TESTE', 'territorio_id':'TER_TESTE',
        'grupo_atividade':'ESCRITORIO', 'cnae_principal':'0000-0/00', 'descricao_cnae':'Teste',
        'porte':'MICRO', 'municipio_real':'Município de teste', 'uf_real':'XX',
        'codigo_ibge_municipio':'0000000', 'tipo_unidade':'MATRIZ',
        'quantidade_unidades':1, 'faturamento_mensal':100000, 'confianca_faturamento':'ALTA',
        'despesa_fixa_mensal_estimada':40000, 'folha_pagamento_mensal':20000,
        'quantidade_funcionarios_estimada':10, 'energia_media_mensal_6m':5000,
        'valor_aluguel_recorrente':5000, 'pagamento_aluguel_recorrente':'SIM',
        'bens_ponderados':30000, 'bens_total_referencia':40000,
        'equipamentos_ponderados':20000, 'equipamentos_total_referencia':25000,
        'informatica_ponderada':10000, 'cozinha_ponderada':0, 'confianca_bens':.9,
        'estoque_medio_estimado':10000, 'estoque_pico_estimado':20000,
        'possui_termo_loja':'NAO', 'possui_termo_galeria':'NAO',
        'material_parede_externa_cadastrado':'ALVENARIA', 'padrao_construtivo_cadastrado':'NORMAL',
        'situacao_imovel_cadastral':'REGULAR', 'endereco_cnpj_compativel':'SIM',
        'area_cadastrada_m2':100, 'dependencia_digital_pct':20,
        'probabilidade_tratamento_dados':.5, 'indice_maturidade_digital':20,
        'seguranca_da_cidade_0_1':.9, 'confianca_territorial_0_1':.6,
        'fonte':'Fixture de teste', 'ano_referencia':'2021',
    }


@pytest.fixture
def catalogo():
    essential = ['INCENDIO_RAIO_EXPLOSAO_FUMACA','DANOS_ELETRICOS','PERDA_PAGAMENTO_ALUGUEL',
        'RESPONSABILIDADE_CIVIL_ESTABELECIMENTO','DESPESAS_FIXAS','PROTECAO_CIBERNETICA_AVALIAR']
    pratico = essential + ['ROUBO_FURTO_ARROMBAMENTO','VENDAVAL_EVENTOS_CORRELATOS']
    total = pratico + ['RESPONSABILIDADE_CIVIL_EMPREGADOR','QUEBRA_DE_VIDROS']
    return pd.DataFrame([{'plano':p,'cobertura_fixa':c} for p,cs in
                        [('ESSENCIAL',essential),('PRATICO',pratico),('TOTAL',total)] for c in cs])


@pytest.fixture
def pasta_csv(tmp_path, registro, catalogo):
    def escrever(nome, linhas, colunas=None):
        df = pd.DataFrame(linhas,columns=colunas)
        df.to_csv(tmp_path/(nome+'.csv'),index=False,encoding='utf-8-sig')
    escrever('dicionario_dados',[{'tabela':'TESTE','campo':'empresa_id','descricao':'Fixture'}])
    escrever('empresas',[{k:registro[k] for k in ['empresa_id','grupo_atividade','cnae_principal',
        'descricao_cnae','porte','faturamento_mensal','confianca_faturamento','quantidade_funcionarios_estimada',
        'dependencia_digital_pct','indice_maturidade_digital']}])
    campos_end = ['empresa_id','imovel_id','territorio_id','tipo_unidade','municipio_real','uf_real',
        'codigo_ibge_municipio','possui_termo_loja','possui_termo_galeria','area_cadastrada_m2',
        'material_parede_externa_cadastrado','padrao_construtivo_cadastrado','situacao_imovel_cadastral','endereco_cnpj_compativel']
    end = [{k:registro[k] for k in campos_end}]
    end += [dict(end[0],imovel_id='IMO_FILIAL',territorio_id='TER_FILIAL',tipo_unidade='FILIAL')]
    escrever('enderecos_estabelecimentos',end)
    campos_sinais = ['empresa_id','imovel_id','valor_aluguel_recorrente','pagamento_aluguel_recorrente',
        'folha_pagamento_mensal','energia_media_mensal_6m','despesa_fixa_mensal_estimada',
        'estoque_medio_estimado','estoque_pico_estimado','probabilidade_tratamento_dados']
    s = {k:registro[k] for k in campos_sinais}
    escrever('sinais_financeiros_operacionais',[s,dict(s,imovel_id='IMO_FILIAL',estoque_medio_estimado=100000)])
    escrever('territorio',[{'territorio_id':e['territorio_id'],'codigo_ibge_municipio':e['codigo_ibge_municipio']} for e in end])
    escrever('bens_cadastrados',[{'bem_id':'BEM_1','empresa_id':'EMP_TESTE','imovel_id_referencia':'IMO_TESTE',
        'tipo_bem':'EQUIPAMENTO_INFORMATICA','valor_cadastrado':100000,
        'probabilidade_bem_no_imovel_referencia':.5,'nivel_confianca_vinculo':'MEDIA',
        'valor_bem_ponderado_referencia':50000}])
    catalogo.to_csv(tmp_path/'catalogo_coberturas_fixas_planos.csv',index=False)
    escrever('template_resultado_times',[],['empresa_id','imovel_id','elegivel','motivo_inelegibilidade',
        'tipo_localizacao_sugerido','relacao_imovel_sugerida','plano_recomendado','coberturas_recomendadas',
        'confianca_geral','justificativa_recomendacao','perguntas_confirmacao','fontes_publicas_adicionais'])
    escrever('template_coberturas_times',[],['empresa_id','imovel_id','cobertura','faixa_valor_min','faixa_valor_max',
        'confianca_estimativa','dados_utilizados','regra_calculo_utilizada','justificativa','informacao_a_confirmar','observacao'])
    return tmp_path
