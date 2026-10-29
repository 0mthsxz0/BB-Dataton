import pandas as pd
from types import SimpleNamespace
from perfil_cnae import perfil_cnae
from cotacao_service import analisar

def sample():
 return SimpleNamespace(estabelecimentos=pd.DataFrame([dict(empresa_id=f'E{i}',imovel_id=f'I{i}_{j}',cnae_principal='1234-5/67',descricao_cnae='Atividade de teste',faturamento_mensal=i*1000,bens_ponderados=100*i,equipamentos_ponderados=50*i) for i in range(1,6) for j in range(2 if i==5 else 1)]))

def test_perfil_agrega_e_nao_identifica_uma_empresa():
 p=perfil_cnae({'cnae':'1234567'},sample())
 assert p['amostra']=={'empresas':5,'estabelecimentos':6}
 assert p['valores']['monthlyRevenue']==3000
 assert p['valores']['contentsValue']==350
 assert p['perguntasConfirmadas']=={}
 assert 'empresaId' not in p and 'imovelId' not in p
 assert 'employees' not in p['valores']

def test_amostra_pequena_nao_vira_dado_do_cliente():
 b=sample();b.estabelecimentos=b.estabelecimentos.iloc[:3]
 assert perfil_cnae({'cnae':'1234567'},b)['valores']=={}
 assert perfil_cnae({'cnae':'9999999'},b)['valores']=={}
