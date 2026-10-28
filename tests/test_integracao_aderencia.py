import copy
import itertools
import json
import subprocess
import sys
from pathlib import Path

import pytest

from motor_pontuacao import MotorPontuacao, DECISORIAS, COMUNS, VIDROS, ROUBO
from processamento import carregar_base
from recomendador import recomendar_plano
from exportacao import analisar_base


def test_quatro_indices_continuos_e_cinco_heuristicas(registro, config):
    motor = MotorPontuacao(config=config)
    pontos = motor.analisar_registro(registro)
    necessidades = motor.necessidades_plano(registro, pontos)
    assert set(pontos) == set(DECISORIAS)
    assert len(necessidades) == 9
    for c in DECISORIAS:
        assert necessidades[c]['prioridade'] == pontos[c]['prioridade']
        assert necessidades[c]['origem'] == 'INDICE_MULTIFATORIAL'
    assert all(necessidades[c]['origem']=='HEURISTICA_PREFERENCIA' for c in COMUNS)


def test_indispensavel_vale_mesmo_com_zero_e_meta_zero(registro, config, catalogo):
    registro = dict(registro, possui_vidros_confirmado='NAO')
    config['planos'].update(meta_aderencia=0, indispensaveis=[VIDROS])
    pontos = MotorPontuacao(config=config).analisar_registro(registro)
    assert pontos[VIDROS]['prioridade']==0
    r = recomendar_plano(pontos,catalogo,config,registro)
    assert r['plano_recomendado']=='TOTAL'
    assert r['necessidades'][VIDROS]['indispensavel']
    assert r['comparacao'][0]['indispensaveis_ausentes']==[VIDROS]
    config['planos']['indispensaveis']=[]
    assert recomendar_plano(pontos,catalogo,config,registro)['plano_recomendado']=='ESSENCIAL'


def test_meta_e_explicacao_exatas_sem_preco(registro, config, catalogo):
    pontos=MotorPontuacao(config=config).analisar_registro(registro)
    for meta in [0,80,100]:
        config['planos']['meta_aderencia']=meta
        r=recomendar_plano(pontos,catalogo,config,registro)
        for plano in r['comparacao']:
            assert plano['aderencia_percentual']==pytest.approx(100*plano['pontos_atendidos']/plano['pontos_totais'])
            assert plano['analise_preco']=='PENDENTE'
        escolhido=next(p for p in r['comparacao'] if p['plano']==r['plano_recomendado'])
        assert escolhido['apto_simulacao']
        assert escolhido['aderencia_percentual']+1e-9>=meta
        assert r['comparacao'][-1]['aderencia_percentual']==pytest.approx(100)
    assert r['plano_recomendado']=='TOTAL'


def test_intervalos_razao_contem_todos_os_extremos(registro,catalogo):
    pontos=MotorPontuacao().analisar_registro(registro)
    r=recomendar_plano(pontos,catalogo,registro=registro)
    itens=list(r['necessidades'].items())
    for escolhas in itertools.product(['prioridade_min','prioridade_max'],repeat=9):
        valores={c:s[k]*s['peso'] for (c,s),k in zip(itens,escolhas)}
        total=sum(valores.values())
        if not total:
            continue
        for p in r['comparacao']:
            codigos=set(catalogo.loc[catalogo.plano.eq(p['plano']),'cobertura_fixa'])
            nota=100*sum(v for c,v in valores.items() if c in codigos)/total
            assert p['aderencia_min_percentual']-1e-8<=nota<=p['aderencia_max_percentual']+1e-8


def test_preferencias_auditadas_e_exportadas(pasta_csv,config):
    config['planos'].update(meta_aderencia=0,indispensaveis=[VIDROS])
    base=carregar_base(pasta_csv)
    r,c,a=analisar_base(base,config)
    assert r.plano_recomendado.eq('TOTAL').all()
    assert len(c)==9*len(r)
    assert all(len(x['pontuacoes'])==4 and len(x['necessidades_plano'])==9 for x in a)
    assert all(x['recomendacao']['indispensaveis']==[VIDROS] for x in a)
    json.dumps(a,allow_nan=False)


def test_cli_preferencias(pasta_csv,tmp_path):
    destino=tmp_path/'saida'
    processo=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'cli.py'),
        '--dados',str(pasta_csv),'--saida',str(destino),'--meta','0','--indispensavel',VIDROS],
        capture_output=True,text=True)
    assert processo.returncode==0,processo.stderr
    manifesto=json.loads((destino/'manifesto.json').read_text(encoding='utf-8'))
    assert manifesto['configuracao']['planos']['indispensaveis']==[VIDROS]
    assert manifesto['configuracao']['planos']['meta_aderencia']==0


@pytest.mark.parametrize('mudanca',[
    lambda c:c['planos'].update(meta_aderencia=float('nan')),
    lambda c:c['planos'].update(meta_aderencia=101),
    lambda c:c['planos'].update(indispensaveis=['INEXISTENTE']),
    lambda c:c['heuristicas_comuns'].update(ancora_despesa_mensal=0)])
def test_regras_invalidas(mudanca,config):
    mudanca(config)
    with pytest.raises(ValueError):
        MotorPontuacao(config=config)
