from produto import personalizar,REGRAS
from motor_pontuacao import MotorPontuacao
from recomendador import recomendar_plano

def calculate(r,catalogo):
 m=MotorPontuacao();rec=recomendar_plano(m.analisar_registro(r),catalogo,registro=r)
 return personalizar(r,rec,{})

def test_protecoes_confirmadas_entram_sem_opt_in(registro,catalogo):
 r=dict(registro,operacao_confirmada={'electronics':True,'signage':True,'cash':False})
 p=calculate(r,catalogo)['pacote']
 assert {'EQUIPAMENTOS_ELETRONICOS','ANUNCIOS_LUMINOSOS'}<=set(p['coberturas_totais'])
 assert 'ROUBO_FURTO_VALORES' not in p['coberturas_totais']
 assert p['quantidade_coberturas']==len(p['coberturas'])+2==len(p['protecoes'])
 assert set(REGRAS['mandatory'])<=set(p['coberturas_totais'])

def test_recusa_prevalece_e_lucros_nao_escolhe_modalidade_ao_acaso(registro,catalogo):
 r=dict(registro,operacao_confirmada={'electronics':True,'interruption':True},adicionais_recusados=['EQUIPAMENTOS_ELETRONICOS'])
 p=calculate(r,catalogo)['pacote']
 assert not p['adicionais_condicionais']
 assert not any(c.startswith('LUCRO_') for c in p['coberturas_totais'])

def test_delivery_confirmado_promove_plano_apenas_para_compatibilidade(registro,catalogo):
 r=dict(registro,operacao_confirmada={'delivery':True})
 p=calculate(r,catalogo)['pacote']
 assert p['plano'] in ('PRATICO','TOTAL')
 assert 'DELIVERY' in p['coberturas_totais']
