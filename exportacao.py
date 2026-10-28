"""Exportação no esquema original dos templates e trilha completa em JSON."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import pandas as pd

from motor_pontuacao import MotorPontuacao
from recomendador import recomendar_plano


def analisar_base(base, config=None):
    motor = MotorPontuacao(base, config)
    resultados, coberturas, auditoria = [], [], []
    for registro in base.estabelecimentos.to_dict('records'):
        pontos = motor.analisar_registro(registro)
        recomendacao = recomendar_plano(pontos, base.catalogo, motor.config, registro)
        aluguel = registro.get('pagamento_aluguel_recorrente') == 'SIM'
        linha = {
            'empresa_id': registro['empresa_id'], 'imovel_id': registro['imovel_id'],
            'elegivel': recomendacao['elegibilidade']['elegivel'],
            'motivo_inelegibilidade': ' | '.join(recomendacao['elegibilidade']['motivos']),
            'tipo_localizacao_sugerido': 'LOJA' if registro.get('possui_termo_loja') == 'SIM' else 'A_CONFIRMAR',
            'relacao_imovel_sugerida': 'INQUILINO_A_CONFIRMAR' if aluguel else 'A_CONFIRMAR',
            'plano_recomendado': recomendacao['plano_recomendado'],
            'coberturas_recomendadas': '|'.join(recomendacao['coberturas']),
            'confianca_geral': round(recomendacao['confianca_geral'], 6),
            'justificativa_recomendacao': recomendacao['justificativa'],
            'perguntas_confirmacao': ' | '.join(recomendacao['perguntas_confirmacao']),
            'fontes_publicas_adicionais': registro.get('fonte') or '',
        }
        resultados.append(linha)
        for codigo in recomendacao['coberturas']:
            s = pontos[codigo]
            coberturas.append({
                'empresa_id': registro['empresa_id'], 'imovel_id': registro['imovel_id'],
                'cobertura': codigo, 'faixa_valor_min': s['faixa_valor_min'],
                'faixa_valor_max': s['faixa_valor_max'], 'confianca_estimativa': s['confianca'],
                'dados_utilizados': json.dumps({'evento': s['fatores_evento'], 'impacto': s['fator_impacto'],
                    'vulnerabilidade': s['fator_vulnerabilidade']}, ensure_ascii=False, allow_nan=False),
                'regra_calculo_utilizada': s['formula'] + ' | ' + s['fator_impacto']['transformacao'],
                'justificativa': s['justificativa'],
                'informacao_a_confirmar': ' | '.join(s['confirmar']),
                'observacao': ' | '.join(s['limitacoes']) + ' Faixas de cenário para análise; não representam preço do seguro ou limite contratual aprovado.',
            })
        auditoria.append({'empresa_id': registro['empresa_id'], 'imovel_id': registro['imovel_id'],
                         'pontuacoes': pontos, 'recomendacao': recomendacao})
    r = pd.DataFrame(resultados, columns=base.templates['template_resultado_times'])
    c = pd.DataFrame(coberturas, columns=base.templates['template_coberturas_times'])
    return r, c, auditoria


def csv_bytes(df):
    return df.to_csv(index=False, lineterminator='\n').encode('utf-8-sig')


def exportar(base, config=None, destino='output'):
    pasta = Path(destino)
    pasta.mkdir(parents=True, exist_ok=True)
    motor = MotorPontuacao(base, config)
    resultados, coberturas, auditoria = analisar_base(base, motor.config)
    arquivos = {'template_resultado_times.csv': csv_bytes(resultados),
                'template_coberturas_times.csv': csv_bytes(coberturas)}
    for nome, conteudo in arquivos.items():
        (pasta / nome).write_bytes(conteudo)
    (pasta / 'auditoria.json').write_text(json.dumps(auditoria, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    config_texto = json.dumps(motor.config, ensure_ascii=False, sort_keys=True, allow_nan=False)
    manifesto = {'versao': motor.config['versao'], 'gerado_em_utc': datetime.now(timezone.utc).isoformat(),
                 'entradas_sha256': base.hashes, 'config_sha256': hashlib.sha256(config_texto.encode()).hexdigest(),
                 'configuracao': motor.config,
                 'saidas_sha256': {n: hashlib.sha256(b).hexdigest() for n, b in arquivos.items()},
                 'estabelecimentos': len(resultados), 'linhas_cobertura': len(coberturas),
                 'avisos': base.avisos}
    (pasta / 'manifesto.json').write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding='utf-8')
    return resultados, coberturas
