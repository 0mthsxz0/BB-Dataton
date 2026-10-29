"""Referência agregada por atividade. Nunca identifica uma empresa pelo CNAE."""
import re
from statistics import median
from processamento import numero
MIN_EMPRESAS=5
CAMPOS={'contentsValue':'bens_ponderados','equipmentValue':'equipamentos_ponderados','stockValue':'estoque_medio_estimado','payroll':'folha_pagamento_mensal','monthlyExpenses':'despesa_fixa_mensal_estimada','monthlyRevenue':'faturamento_mensal','rentValue':'valor_aluguel_recorrente'}
def perfil_cnae(payload,base):
 if not isinstance(payload,dict) or not isinstance(payload.get('cnae'),str):raise ValueError('Informe o código da atividade com sete dígitos.')
 code=re.sub(r'[-./\s]','',payload['cnae'])
 if not re.fullmatch(r'\d{7}',code):raise ValueError('Informe o código da atividade com sete dígitos.')
 rows=[] if base is None else [r for r in base.estabelecimentos.to_dict('records') if re.sub(r'\D','',str(r.get('cnae_principal','')))==code]
 companies={r['empresa_id'] for r in rows}
 result={'versao':'perfil-cnae-mediana-1','cnae':code,'encontrado':bool(rows),'amostra':{'empresas':len(companies),'estabelecimentos':len(rows)},'valores':{},'descricao':str(rows[0].get('descricao_cnae','')) if rows else '', 'origem':'Perfil agregado dos CSVs de desenvolvimento do Datathon; empresas fictícias.', 'metodo':'Mediana por estabelecimento; faturamento calculado uma vez por empresa. Mínimo de cinco empresas por perfil.', 'perguntasConfirmadas':{}}
 if len(companies)<MIN_EMPRESAS:
  result['aviso']='Não há amostra suficiente para preencher valores de referência. Continue com os dados da sua empresa.'
  return result
 for field,col in CAMPOS.items():
  sample=rows
  if field=='monthlyRevenue':sample=list({r['empresa_id']:r for r in rows}.values())
  valid=[numero(r.get(col)) for r in sample if numero(r.get(col)) is not None]
  if len(valid)>=MIN_EMPRESAS:result['valores'][field]=round(median(valid),2)
 result['aviso']='Valores de referência da atividade, não dados confirmados da sua empresa. Revise e altere quando necessário. Não usamos o CNAE para identificar um cliente.'
 return result
