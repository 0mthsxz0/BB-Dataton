"""Avaliação Mosler técnica declarada, complementar à recomendação.

Não estima notas pelos dados cadastrais e não usa um índice CRITIC como agressão.
Este contrato manual é distinto da adaptação SINESP ponderada da branch de dados.
"""
from datetime import date


def avaliar_mosler(avaliacao=None,data_analise=None):
    hoje=date.fromisoformat(data_analise) if isinstance(data_analise,str) else data_analise or date.today()
    saida={'modelo':'mosler-tecnico-declarado-1.0','status':'PENDENTE_AVALIACAO',
        'aplicada_na_recomendacao':False,'criterios':None,'er':None,'indice_0_100':None,'faixa':None,
        'motivos':['Avaliação técnica F, S, P, E, A e V com evidências ainda não registrada.'],
        'aviso':'Pontuação experimental de prioridade, sem interpretação de probabilidade. Não altera automaticamente plano ou adicionais.'}
    if not avaliacao:return saida
    try:
        criterios=avaliacao['criterios']
        notas={k:criterios[k]['nota'] for k in 'FSPEAV'}
        if set(criterios)!=set('FSPEAV') or any(type(v) is not int or not 1<=v<=5 for v in notas.values()):raise ValueError()
        if any(not isinstance(criterios[k]['evidencia'],str) or not 3<=len(criterios[k]['evidencia'].strip())<=2000 for k in notas):raise ValueError()
        if not isinstance(avaliacao['avaliador'],str) or not 2<=len(avaliacao['avaliador'].strip())<=100:raise ValueError()
        quando=date.fromisoformat(avaliacao['data_avaliacao'])
        if quando>hoje:raise ValueError()
        er=(notas['F']*notas['S']+notas['P']*notas['E'])*notas['A']*notas['V']
        faixa='muito baixo' if er<=250 else 'baixo' if er<=500 else 'normal' if er<=750 else 'alto' if er<=1000 else 'muito alto'
        return {**saida,'status':'EXPERIMENTAL_NAO_CALIBRADO','criterios':criterios,'er':er,
                'indice_0_100':100*(er-2)/1248,'faixa':faixa,'avaliador':avaliacao['avaliador'],
                'data_avaliacao':quando.isoformat(),'motivos':['Notas técnicas declaradas; ausência de validação atuarial.']}
    except (KeyError,ValueError,TypeError,AttributeError):
        return {**saida,'status':'AVALIACAO_INVALIDA','motivos':['Exige seis notas inteiras de 1 a 5, evidência por critério, responsável e data válida.']}
