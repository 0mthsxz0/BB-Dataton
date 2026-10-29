"""Motor determinístico: evento, impacto e vulnerabilidade permanecem separados."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import copy
import json
import math
from datetime import date
from seguranca import avaliar_seguranca
from contexto_seguranca import IntegracaoSeguranca
from avaliacao_mosler import avaliar_mosler

from processamento import BaseDados, NULOS, carregar_base, numero

CONFIG_PADRAO = Path(__file__).with_name('config_regras.json')
INCENDIO = 'INCENDIO_RAIO_EXPLOSAO_FUMACA'
ELETRICO = 'DANOS_ELETRICOS'
ALUGUEL = 'PERDA_PAGAMENTO_ALUGUEL'
TERCEIROS = 'RESPONSABILIDADE_CIVIL_ESTABELECIMENTO'
DESPESAS = 'DESPESAS_FIXAS'
ROUBO = 'ROUBO_FURTO_ARROMBAMENTO'
VENDAVAL = 'VENDAVAL_EVENTOS_CORRELATOS'
EMPREGADOR = 'RESPONSABILIDADE_CIVIL_EMPREGADOR'
VIDROS = 'QUEBRA_DE_VIDROS'
CIBER = 'PROTECAO_CIBERNETICA_AVALIAR'
DECISORIAS = (ROUBO, VENDAVAL, EMPREGADOR, VIDROS)
COMUNS = (INCENDIO, ELETRICO, ALUGUEL, TERCEIROS, DESPESAS, CIBER)


def limitar(x):
    return max(0., min(1., float(x)))


def carregar_config(caminho=None):
    if isinstance(caminho, dict):
        cfg = copy.deepcopy(caminho)
    else:
        cfg = json.loads(Path(caminho or CONFIG_PADRAO).read_text(encoding='utf-8-sig'))
    validar_config(cfg)
    return cfg


def validar_config(cfg):
    """Rejeita parâmetros inválidos antes de qualquer processamento."""
    def finito(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
    if cfg.get('versao')!='0.4.0':
        raise ValueError('Configuração incompatível. Use o modelo v0.4.0: quatro índices e dez necessidades.')
    m = cfg['modelo']
    for chave in ['piso_evento', 'piso_impacto', 'piso_vulnerabilidade', 'interacao_maxima',
                  'risco_ausente', 'vulnerabilidade_ausente']:
        if not finito(m[chave]) or not 0 <= m[chave] <= 1:
            raise ValueError(f'Parâmetro fora de 0 a 1: {chave}')
    if not finito(m['escala_monetaria']) or m['escala_monetaria'] <= 0:
        raise ValueError('Escala monetária deve ser positiva.')
    for v in cfg['normalizacao'].values():
        if not finito(v) or v <= 0:
            raise ValueError('Referências de normalização devem ser positivas.')
    c = cfg['cenarios']
    if not 0 < c['meses_paralisacao_min'] <= c['meses_paralisacao_max']:
        raise ValueError('Cenários de paralisação inconsistentes.')
    p = cfg['planos']
    if not finito(p['limiar_cobertura']) or not 0 <= p['limiar_cobertura'] <= 100:
        raise ValueError('Limiares dos planos inconsistentes.')
    if not finito(p['meta_aderencia']) or not 0 <= p['meta_aderencia'] <= 100:
        raise ValueError('Meta de aderência deve estar entre 0 e 100.')
    if (not isinstance(p['indispensaveis'], list) or
            any(not isinstance(c, str) or c not in cfg['coberturas'] for c in p['indispensaveis'])):
        raise ValueError('Cobertura indispensável inválida.')
    h = cfg['heuristicas_comuns']
    if not finito(h['ancora_despesa_mensal']) or h['ancora_despesa_mensal'] <= 0:
        raise ValueError('Âncora de despesas deve ser positiva.')
    for chave, valor in h.items():
        if chave != 'ancora_despesa_mensal' and (not finito(valor) or not 0 <= valor <= 100):
            raise ValueError(f'Heurística inválida: {chave}')
    if h['base_eletrico'] + h['amplitude_eletrico'] > 100 or h['base_despesas'] + h['amplitude_despesas'] > 100:
        raise ValueError('Heurísticas devem produzir no máximo 100 pontos.')
    limites = [x['limite'] for x in cfg['classes']]
    if limites != sorted(set(limites)) or limites[-1] <= 100:
        raise ValueError('Classes devem ser crescentes e cobrir a nota 100.')
    if set(cfg['coberturas']) != {INCENDIO, ELETRICO, ALUGUEL, TERCEIROS, DESPESAS,
                                 ROUBO, VENDAVAL, EMPREGADOR, VIDROS, CIBER}:
        raise ValueError('Configuração deve conter dez coberturas: quatro índices e seis heurísticas.')
    for codigo, regra in cfg['coberturas'].items():
        pesos = list(regra['pesos_evento'].values())
        if codigo in DECISORIAS and (not pesos or any(not finito(x) or x < 0 for x in pesos) or not math.isclose(sum(pesos), 1)):
            raise ValueError(f'Pesos de {codigo} devem somar 1 e ser não negativos.')
        if regra['papel'] != ('decisao' if codigo in DECISORIAS else 'dimensionamento'):
            raise ValueError(f'Papel incorreto para {codigo}.')
        if not finito(regra['referencia_financeira']) or regra['referencia_financeira'] <= 0:
            raise ValueError(f'Referência financeira inválida: {codigo}')
        if not 0 <= regra['coeficiente_interacao'] <= m['interacao_maxima']:
            raise ValueError(f'Interação inválida: {codigo}')
        if not finito(regra['peso_plano']) or regra['peso_plano'] <= 0:
            raise ValueError(f'Peso do plano inválido: {codigo}')
    for grupo in [*cfg['atividades'].values(), cfg['materiais'], cfg['padroes'], cfg['confiancas']]:
        if any(not finito(v) or not 0 <= v <= 1 for v in grupo.values()):
            raise ValueError('Mapas categóricos devem conter valores de 0 a 1.')
    clima=cfg['clima']
    if (any(not finito(clima[k]) or clima[k]<=0 for k in ['rajada_forte_kmh','rajada_severa_kmh','rajada_chuva_kmh','chuva_mm','referencia_frequencia'])
            or not 0 < clima['rajada_chuva_kmh'] <= clima['rajada_forte_kmh'] < clima['rajada_severa_kmh']
            or clima['chuva_mm'] <= 0 or clima['referencia_frequencia'] <= 0
            or len(clima['pesos'])!=3 or any(not finito(x) or x<0 for x in clima['pesos'])
            or not math.isclose(sum(clima['pesos']),1)):
        raise ValueError('Parâmetros climáticos inconsistentes.')
    if set(cfg['nr4']['pesos_grau'])!={'1','2','3','4'} or any(not finito(x) or not 0<=x<=1 for x in cfg['nr4']['pesos_grau'].values()):
        raise ValueError('Mapa de grau NR-4 inválido.')
    if not finito(cfg['nr4']['confianca_classificacao']) or not 0<=cfg['nr4']['confianca_classificacao']<=1:
        raise ValueError('Confiança da referência NR-4 inválida.')


def normalizar_financeiro(valor, referencia, escala=10000):
    n = numero(valor)
    if n is None:
        return None
    return limitar(math.log1p(n / escala) / math.log1p(referencia / escala))


@dataclass(frozen=True)
class Fator:
    nome: str
    valor_original: object
    valor_normalizado: float
    confianca: float
    transformacao: str
    observacao: str = ''

    def limites(self):
        # Sensibilidade à evidência incompleta, não intervalo estatístico.
        return (self.valor_normalizado * self.confianca,
                self.valor_normalizado + (1 - self.confianca) * (1 - self.valor_normalizado))


def fator(nome, original, normalizado, confianca=1., transformacao='Escala 0 a 1', observacao=''):
    ausente = normalizado is None
    return Fator(nome, original, .5 if ausente else limitar(normalizado),
                 0. if ausente else limitar(confianca), transformacao, observacao)


def soma_observada(*valores):
    presentes = [numero(x) for x in valores if numero(x) is not None]
    return sum(presentes) if presentes else None


class MotorPontuacao:
    def __init__(self, base: BaseDados | None = None, config=None, data_analise=None,
                 banco_seguranca=None, modo_seguranca=None):
        self.base = base
        self.config = carregar_config(config)
        self.data_analise = date.fromisoformat(data_analise) if isinstance(data_analise,str) else (data_analise or date.today())
        self.integracao_seguranca = IntegracaoSeguranca(banco_seguranca, modo_seguranca)

    def preparar_registro(self, registro):
        return self.integracao_seguranca.preparar(registro, self.data_analise)

    def fatores(self, r):
        cfg = self.config
        f = {}
        grupo = r.get('grupo_atividade')
        for tipo in ['incendio', 'terceiros', 'ocupacional']:
            v = cfg['atividades'][tipo].get(grupo)
            f['atividade_' + tipo] = fator('Atividade: ' + tipo, grupo, v, .65,
                'Mapa configurável de atividade', 'Hipótese de exposição; não é taxa histórica de sinistro.')
        grau=numero(r.get('grau_risco_nr4'))
        peso=cfg['nr4']['pesos_grau'].get(str(int(grau))) if grau in (1,2,3,4) else None
        f['atividade_ocupacional']=fator('Classificação ocupacional NR-4',grau,peso,
            cfg['nr4']['confianca_classificacao'],'Mapa de grau ordinal NR-4 configurável',
            str(r.get('fonte_nr4') or 'Sem referência NR-4 para o CNAE')+
            '; classificação de atividade, não probabilidade de acidente ou responsabilidade jurídica.')
        for chave, coluna, mapa in [('material', 'material_parede_externa_cadastrado', cfg['materiais']),
                                   ('padrao', 'padrao_construtivo_cadastrado', cfg['padroes'])]:
            f[chave] = fator(coluna, r.get(coluna), mapa.get(r.get(coluna)), .8, 'Mapa construtivo configurável')
        for chave, coluna in [('energia', 'energia_media_mensal_6m'),
                              ('funcionarios', 'quantidade_funcionarios_estimada')]:
            ref = cfg['normalizacao'][chave]
            n = numero(r.get(coluna))
            if chave=='funcionarios':
                local=numero(r.get('funcionarios_unidade_confirmados'))
                n=local if local is not None else (n if numero(r.get('quantidade_unidades'))==1 else None)
            v = None if n is None else limitar(n / ref)
            f[chave] = fator(coluna, r.get(coluna), v, .65,
                f'min(valor / {ref}, 1)', 'Indicador indireto; funcionários no nível da empresa.' if chave == 'funcionarios' else 'Despesa de energia; não comprova falha elétrica ou consumo físico.')
        loja = r.get('possui_termo_loja')
        galeria = r.get('possui_termo_galeria')
        v = .85 if 'SIM' in (loja, galeria) else (.25 if loja == galeria == 'NAO' else None)
        f['presenca_loja'] = fator('Sinais de loja ou galeria', [loja, galeria], v, .55,
            'SIM: 0,85; ambos NAO: 0,25', 'Não comprova fluxo de clientes nem existência ou quantidade de vidros.')
        dep = numero(r.get('dependencia_digital_pct'))
        f['dependencia_digital'] = fator('Dependência digital', dep, dep / 100 if dep is not None and dep <= 100 else None, .7, 'percentual / 100')
        # Usa um representante por fenômeno. Não soma os vários índices digitais derivados.
        dados = numero(r.get('probabilidade_tratamento_dados'))
        f['exposicao_ciber'] = fator('Exposição digital contextual', dados,
            dados if dados is not None and dados <= 1 else None, .5,
            'Indicador de tratamento de dados em escala 0 a 1',
            'Não mede probabilidade de ataque. Maturidade digital não é controle técnico comprovado.')
        for chave, coluna, inverter in [('exposicao_territorial', 'seguranca_da_cidade_0_1', True),
                                       ('exposicao_climatica', 'exposicao_climatica_0_1', False)]:
            tipo='seguranca' if inverter else 'clima'
            confianca_territorio = numero(r.get(f'confianca_{tipo}_0_1',r.get('confianca_territorial_0_1')))
            n = numero(r.get(coluna))
            observacao_clima=''
            if inverter:
                qualidade = avaliar_seguranca(r, self.data_analise)
                observacao_clima = ' ' + ' '.join(qualidade['motivos'])
                if not qualidade['utilizavel']:
                    n = None
            if not inverter and r.get('metodologia_clima'):
                try:
                    origem=json.loads(r['metodologia_clima'])
                    chaves=['inicio','fim','rajada_forte_kmh','rajada_severa_kmh','rajada_chuva_kmh','chuva_mm']
                    if any(origem.get(k)!=cfg['clima'][k] for k in chaves):
                        n=None
                        observacao_clima=' Parâmetros climáticos divergentes: regenerar referências; valor não utilizado.'
                    elif origem!=cfg['clima']:
                        fs=[numero(r.get(k)) for k in ['frequencia_rajada_forte','frequencia_rajada_severa','frequencia_vento_chuva']]
                        if all(x is not None for x in fs):
                            bruto=sum(w*x for w,x in zip(cfg['clima']['pesos'],fs))
                            n=bruto/(bruto+cfg['clima']['referencia_frequencia'])
                        else:
                            n=None
                            observacao_clima=' Sem frequências para recalcular os novos parâmetros.'
                except (ValueError,TypeError):
                    n=None
                    observacao_clima=' Metodologia climática inválida; valor não utilizado.'
            v = (1 - n if inverter else n) if n is not None and n <= 1 else None
            f[chave] = fator(coluna, n, v, confianca_territorio or 0.,
                '1 - segurança relativa' if inverter else 'Indicador climático documentado',
                'Fonte externa: ' + str(r.get(f'fonte_{tipo}',r.get('fonte')) or 'não integrada') + '; período: ' + str(r.get(f'periodo_{tipo}',r.get('ano_referencia')) or 'não informado') + '. Não representa probabilidade empresarial.'+observacao_clima)
        confirmado=r.get('possui_vidros_confirmado')
        if confirmado in ('SIM','NAO'):
            f['presenca_loja']=fator('Presença de vidros confirmada',confirmado,1 if confirmado=='SIM' else 0,
                .9,'Confirmação específica do estabelecimento','Não informa por si só o valor de reposição.')
        return f

    def vulnerabilidade(self, r):
        despesas = numero(r.get('despesa_fixa_mensal_estimada'))
        receita = numero(r.get('faturamento_mensal'))
        unidades = numero(r.get('quantidade_unidades'))
        if unidades != 1 or despesas is None or receita is None or receita == 0:
            return fator('Vulnerabilidade financeira', None, None, observacao=
                'Sem caixa e reservas. Não divide faturamento empresarial entre filiais arbitrariamente.')
        confianca = self.config['confiancas'].get(r.get('confianca_faturamento'), .3)
        return fator('Comprometimento operacional', {'despesas_unidade': despesas, 'receita_empresa': receita},
            despesas / receita, min(.4, confianca), 'min(despesa fixa / faturamento, 1), somente empresa de uma unidade',
            'Proxy limitada: faturamento não é lucro, liquidez ou capacidade comprovada de absorção da perda.')

    def impacto(self, r, regra, f):
        tipo = regra['exposicao']
        meses = self.config['cenarios']
        media = numero(r.get('estoque_medio_estimado'))
        pico = numero(r.get('estoque_pico_estimado'))
        bens = numero(r.get('bens_ponderados'))
        total = numero(r.get('bens_total_referencia'))
        equipamentos = numero(r.get('equipamentos_ponderados'))
        custos = numero(r.get('despesa_fixa_mensal_estimada'))
        cb = numero(r.get('confianca_bens')) or 0.
        dados = {}
        nota = ''
        minimo = maximo = None
        confianca = .5
        if tipo in ('patrimonio', 'roubavel'):
            valor = soma_observada(bens, media)
            dados = {'bens_ponderados': bens, 'estoque_medio': media, 'estoque_pico': pico,
                     'bens_total_referencia': total}
            confianca = (cb + (.6 if media is not None else 0)) / 2
            minimo = valor
            maximo = soma_observada(total, max(x for x in [media, pico] if x is not None) if media is not None or pico is not None else None)
            nota = 'Conteúdo cadastrado e estoque, sem valor de reconstrução do prédio. Confirmar bens cobertos, suscetibilidade à subtração e sobreposição com estoque.'
            predio = numero(r.get('valor_predio_reposicao_brl'))
            if tipo == 'patrimonio' and predio is not None:
                valor = soma_observada(valor, predio)
                minimo = valor
                maximo = soma_observada(maximo, predio)
                dados['valor_predio_reposicao_brl'] = predio
                nota = 'Conteúdo e estoque, acrescidos do valor de reconstrução informado, sem terreno. Confirmar reposição e sobreposição dos itens.'
        elif tipo == 'equipamentos':
            valor = equipamentos
            dados = {'equipamentos_ponderados': equipamentos,
                     'equipamentos_total_referencia': numero(r.get('equipamentos_total_referencia'))}
            confianca = cb
            minimo, maximo = valor, dados['equipamentos_total_referencia']
            nota = 'Equipamentos das categorias elétricas cadastradas; confirmar reposição e interesse segurado.'
        elif tipo in ('despesas', 'aluguel'):
            mensal = custos if tipo == 'despesas' else numero(r.get('valor_aluguel_recorrente'))
            if tipo == 'aluguel' and (mensal == 0 or r.get('pagamento_aluguel_recorrente') != 'SIM'):
                mensal = None
            valor = mensal * meses['meses_paralisacao_max'] if mensal is not None else None
            minimo = mensal * meses['meses_paralisacao_min'] if mensal is not None else None
            maximo = valor
            confianca = .6 if mensal is not None else 0
            dados = {'valor_mensal': mensal, **meses}
            nota = ('Cenários de paralisação configuráveis; despesas agregadas sem somar novamente aluguel e folha.'
                    if tipo == 'despesas' else 'Ausência de aluguel não comprova imóvel próprio. Confirmar relação com imóvel, contrato e aplicabilidade.')
        elif tipo == 'digital':
            dep = f['dependencia_digital']
            it = numero(r.get('informatica_ponderada'))
            valor = soma_observada(it, custos * dep.valor_normalizado * meses['meses_paralisacao_max']
                                  if custos is not None and dep.confianca else None)
            dados = {'informatica_ponderada': it, 'despesa_fixa': custos,
                     'dependencia_digital_pct': r.get('dependencia_digital_pct')}
            confianca = .35 if valor is not None else 0
            minimo = maximo = None
            nota = 'Cenário operacional parcial, sem converter equipamentos e interrupção em limite de indenização cibernética. Faixa depende de condições e cenários contratuais; confirmar exposição a dados, recuperação e terceiros.'
        else:
            # Não converte folha ou área em indenização fictícia.
            if tipo == 'empregador':
                folha = numero(r.get('folha_pagamento_mensal'))
                v = normalizar_financeiro(folha, self.config['normalizacao']['folha'])
                dados = {'folha_pagamento_mensal': folha, 'funcionarios_empresa': r.get('quantidade_funcionarios_estimada')}
                confianca = .4 if folha is not None else 0
            elif tipo == 'terceiros':
                # A atividade já entra no evento. Não a conta novamente como dinheiro.
                v = None
                dados = {'atividade': r.get('grupo_atividade')}
                confianca = 0
            else:
                valor=numero(r.get('valor_vidros_reposicao_brl'))
                if r.get('possui_vidros_confirmado')=='NAO':
                    valor=0.
                v=normalizar_financeiro(valor,regra['referencia_financeira'],self.config['modelo']['escala_monetaria'])
                dados = {'valor_vidros_reposicao_brl':valor,'possui_vidros_confirmado':r.get('possui_vidros_confirmado'),
                         'possui_termo_loja': r.get('possui_termo_loja'), 'possui_termo_galeria': r.get('possui_termo_galeria')}
                confianca = .85 if valor is not None else 0
                if valor is not None:
                    return fator('Reposição de vidros informada',dados,v,confianca,
                        'Normalização logarítmica do valor de reposição informado',
                        'Confirmar orçamento e itens contratualmente cobertos.'),valor,valor,valor
            nota = 'Magnitude financeira não observada. Proxy contextual para triagem; confirmar cenários de danos e valores. Faixa monetária sem base defensável nesta versão.'
            return fator('Impacto financeiro contextual', dados, v, confianca,
                         'Proxy contextual, sem estimativa de indenização', nota), None, None, None
        transformacao = f'log1p(valor / {self.config["modelo"]["escala_monetaria"]}) / log1p({regra["referencia_financeira"]} / escala), limitado a 1'
        v = normalizar_financeiro(valor, regra['referencia_financeira'], self.config['modelo']['escala_monetaria'])
        impacto = fator('Impacto financeiro do cenário', dados, v, confianca, transformacao, nota)
        return impacto, valor, minimo, maximo

    def analisar_registro(self, r):
        r = self.preparar_registro(r)
        cfg = self.config
        f = self.fatores(r)
        v = self.vulnerabilidade(r)
        saida = {}
        for codigo, regra in cfg['coberturas'].items():
            if codigo not in DECISORIAS:
                continue
            pesos = regra['pesos_evento']
            evento = sum(f[chave].valor_normalizado * peso for chave, peso in pesos.items())
            ce = sum(f[chave].confianca * peso for chave, peso in pesos.items())
            el = sum(f[chave].limites()[0] * peso for chave, peso in pesos.items())
            eh = sum(f[chave].limites()[1] * peso for chave, peso in pesos.items())
            impacto, valor, minimo, maximo = self.impacto(r, regra, f)
            i = impacto.valor_normalizado
            vv = v.valor_normalizado if v.confianca else cfg['modelo']['vulnerabilidade_ausente']
            vulnerabilidade=v
            if codigo==VENDAVAL:
                fisico=f['padrao']
                vv=.6*vv+.4*fisico.valor_normalizado
                vulnerabilidade=fator('Vulnerabilidade financeira e construtiva',
                    {'financeira':asdict(v),'construtiva':asdict(fisico)},vv,
                    .6*v.confianca+.4*fisico.confianca,
                    '0,60 × proxy financeira + 0,40 × padrão construtivo',
                    'Resistência do telhado não documentada; padrão construtivo é apenas proxy.')
                q = r.get('questionario')
                if q:
                    vv = .5 * vv + .25 * (not q['roofMaintained']) + .25 * q['exposedAssets']
                    vulnerabilidade = fator('Condições financeiras, construtivas e exposição ao vento',
                        {'componente_mvp':asdict(vulnerabilidade), 'roofMaintained':q['roofMaintained'],
                         'exposedAssets':q['exposedAssets']}, vv, .5*vulnerabilidade.confianca+.5*.8,
                        '0,50 × vulnerabilidade MVP + 0,25 × ausência de manutenção + 0,25 × bens expostos',
                        'Respostas declaradas pelo usuário; não substituem vistoria.')
            # Para riscos ausentes, ponto central explícito e faixa ampla, nunca zero automático.
            if ce == 0:
                evento = cfg['modelo']['risco_ausente']
            interacao = regra['interacao']
            if interacao == 'cozinha':
                cozinha = numero(r.get('cozinha_ponderada'))
                d = limitar(cozinha / max(1, numero(r.get('bens_ponderados')) or 1)) if cozinha is not None else 0
                descricao_j = 'Equipamentos de cozinha observados × exposição ao evento × impacto'
            elif interacao == 'digital':
                d = f['dependencia_digital'].valor_normalizado
                descricao_j = 'Dependência digital × exposição ao evento × impacto'
            elif interacao == 'presencial':
                d = f['presenca_loja'].valor_normalizado
                descricao_j = 'Sinal presencial × exposição ao evento × impacto'
            elif interacao == 'ocupacional':
                d = f['funcionarios'].valor_normalizado
                descricao_j = 'Trabalhadores expostos × atividade × impacto'
            elif interacao == 'custos':
                d = vv
                descricao_j = 'Comprometimento operacional × exposição ao evento × impacto'
            else:
                d = 0
                descricao_j = 'Sem interação adicional; os componentes já se multiplicam'
            coef = regra['coeficiente_interacao']
            a, b = cfg['modelo']['piso_evento'], cfg['modelo']['piso_vulnerabilidade']
            p = cfg['modelo']['piso_impacto']
            def pontuar(iv, rv, vulnerabilidade, dependencia):
                return 100 * limitar((p+(1-p)*iv) * (a + (1-a)*rv) * (b + (1-b)*vulnerabilidade)
                                     + coef * iv * rv * dependencia)
            prioridade = pontuar(i, evento, vv, d)
            il, ih = impacto.limites()
            vl, vh = vulnerabilidade.limites()
            # Todos os termos são não negativos: extremos dão limites conservadores.
            baixo, alto = pontuar(il, el, vl, 0), pontuar(ih, eh, vh, 1 if interacao else 0)
            sem_exposicao = ((codigo==VIDROS and r.get('possui_vidros_confirmado')=='NAO') or
                             (codigo==EMPREGADOR and r.get('possui_empregados_confirmado')=='NAO') or
                             (codigo==ROUBO and r.get('escopo_protecao')=='building'))
            if sem_exposicao:
                baixo=alto=0.
            base_pontos = 100 * (p+(1-p)*i) * (a + (1-a)*evento) * (b + (1-b)*vv)
            j_pontos = 100 * coef * i * evento * d
            if sem_exposicao:
                prioridade=baixo=alto=base_pontos=j_pontos=0.
            confianca = (ce + impacto.confianca + vulnerabilidade.confianca) / 3
            nivel = next(cl['nome'] for cl in cfg['classes'] if prioridade < cl['limite'])
            usados = [dict(asdict(f[chave]), peso_evento=peso,
                            contribuicao_evento=f[chave].valor_normalizado * peso) for chave, peso in pesos.items()]
            limitacoes = [impacto.observacao, vulnerabilidade.observacao,
                          'Índice de prioridade, sem interpretação como probabilidade de sinistro.']
            if codigo == ROUBO:
                limitacoes.extend(avaliar_seguranca(r, self.data_analise)['motivos'])
            if ce < .6:
                limitacoes.append('Componente do evento com evidência limitada; conferir fatores ausentes e origem dos dados.')
            if codigo in (CIBER, ELETRICO):
                limitacoes.append('Dependência digital é indicador operacional; não comprova controles de segurança.')
            if codigo == EMPREGADOR and numero(r.get('quantidade_unidades')) != 1:
                limitacoes.append('Funcionários informados por empresa; distribuição entre unidades não observada.')
            if valor is not None and valor > regra['referencia_financeira']:
                limitacoes.append('Impacto normalizado atingiu o limite; consultar o valor bruto, que foi preservado.')
            justificativa = (f'{regra["nome"]}: prioridade {prioridade:.1f}% ({nivel.lower()}). '
                             f'Componente relativo do evento {evento*100:.1f}%; impacto {i*100:.1f}%; '
                             f'vulnerabilidade estimada {vv*100:.1f}%. Base {base_pontos:.2f} pontos percentuais '
                             f'+ interação {j_pontos:.2f} pontos percentuais, limitada a 100%. '
                             f'Confiança {confianca:.0%}.')
            if codigo==VIDROS and r.get('possui_vidros_confirmado')=='NAO':
                justificativa+=' Ausência de vidros informada na confirmação da unidade; sem exposição identificada.'
            if codigo==EMPREGADOR and r.get('possui_empregados_confirmado')=='NAO':
                justificativa+=' Ausência de empregados informada na unidade; sem exposição identificada para responsabilidade civil do empregador.'
            if codigo==ROUBO and r.get('escopo_protecao')=='building':
                justificativa+=' Conteúdo excluído pelo escopo de proteção somente do imóvel.'
            if codigo==ROUBO:
                campos=['fonte_seguranca','periodo_seguranca','granularidade_seguranca','metodologia_seguranca',
                        'taxa_furto_domicilios','taxa_roubo_domicilios','roubo_comercio_total',
                        'taxa_por_mil_estabelecimentos','estabelecimentos_referencia',
                        'referencia_taxa_por_mil','regioes_fonte','sha256_arquivos','atualizado_em_utc','indicador_disponivel']
            elif codigo==VENDAVAL:
                campos=['fonte_clima','periodo_clima','granularidade_clima','metodologia_clima','modelo_clima',
                        'latitude_publica','longitude_publica','latitude_celula','longitude_celula',
                        'dias_esperados','dias_vento_validos','dias_conjuntos_validos',
                        'frequencia_rajada_forte','frequencia_rajada_severa','frequencia_vento_chuva','sha256_serie']
            elif codigo==EMPREGADOR:
                campos=['cnae_principal','classe_cnae','grau_risco_nr4','fonte_nr4','versao_nr4','pagina','sha256_documento']
            else:
                campos=['possui_vidros_confirmado','valor_vidros_reposicao_brl']
            saida[codigo] = {
                'cobertura': codigo, 'nome': regra['nome'], 'prioridade': round(prioridade, 4),
                'prioridade_0_1': prioridade/100,
                'classe': nivel, 'risco_evento_relativo': round(evento, 6),
                'probabilidade_sinistro': None, 'risco_evento_observado': ce > 0,
                'confianca_evento': ce, 'impacto_normalizado': i,
                'valor_exposto_brl': valor, 'vulnerabilidade': vv,
                'confianca': round(confianca, 6),
                'prioridade_min': round(baixo, 4), 'prioridade_max': round(alto, 4),
                'faixa_valor_min': minimo, 'faixa_valor_max': maximo,
                'adicional': regra['adicional'], 'fatores_evento': usados,
                'referencia_evento':{c:r.get(c) for c in campos},
                'fator_impacto': asdict(impacto), 'fator_vulnerabilidade': asdict(vulnerabilidade),
                'decomposicao': {'base_pontos': base_pontos, 'interacao_pontos': j_pontos,
                    'efeito_limite_pontos': prioridade-base_pontos-j_pontos,
                    'coeficiente_interacao': coef, 'dependencia_interacao': d,
                    'descricao_interacao': descricao_j, 'piso_evento': a, 'piso_impacto':p,'piso_vulnerabilidade': b},
                'formula': '100 * clip((p+(1-p)*I) * (a+(1-a)*R) * (b+(1-b)*V) + k*I*R*D, 0, 1)',
                'justificativa': justificativa, 'limitacoes': limitacoes,
                'confirmar': list(dict.fromkeys([x for x in limitacoes if 'confirmar' in x.lower() or 'sem caixa' in x.lower() or 'não observad' in x.lower()])),
            }
            if codigo == ROUBO:
                saida[codigo]['qualidade_seguranca'] = avaliar_seguranca(r, self.data_analise)
                saida[codigo]['contexto_seguranca'] = r['contexto_seguranca']
                saida[codigo]['avaliacao_mosler'] = avaliar_mosler(r.get('avaliacao_mosler'), self.data_analise)
                saida[codigo]['risco_territorial_observado'] = saida[codigo]['qualidade_seguranca']['status'] == 'EXPERIMENTAL'
        return saida

    def dimensionar_coberturas(self,r):
        """Dimensiona as dez coberturas, sem criar índices para as seis comuns."""
        f=self.fatores(r)
        dimensoes={}
        for codigo,regra in self.config['coberturas'].items():
            impacto,valor,minimo,maximo=self.impacto(r,regra,f)
            dimensoes[codigo]={'cobertura':codigo,'nome':regra['nome'],
                'papel':regra['papel'],'valor_exposto_brl':valor,
                'faixa_valor_min':minimo,'faixa_valor_max':maximo,'confianca':impacto.confianca,
                'fator_impacto':asdict(impacto),'formula':impacto.transformacao,
                'justificativa':f'{regra["nome"]}: dimensionamento por cenário. '+impacto.observacao,
                'limitacoes':[impacto.observacao], 'confirmar':[impacto.observacao]}
        return dimensoes

    def necessidades_plano(self, r, pontuacoes=None):
        """Dez necessidades; quatro índices físicos e seis heurísticas explícitas."""
        pontos = self.analisar_registro(r) if pontuacoes is None else pontuacoes
        saida = {c: {'nome': s['nome'], 'prioridade': s['prioridade'],
            'prioridade_min': s['prioridade_min'], 'prioridade_max': s['prioridade_max'],
            'confianca': s['confianca'], 'origem': 'INDICE_MULTIFATORIAL',
            'formula': s['formula'], 'dados': {'referencia_evento': s['referencia_evento']},
            'justificativa': s['justificativa']} for c, s in pontos.items() if c in DECISORIAS}
        h = self.config['heuristicas_comuns']

        def incluir(codigo, valor, confianca, formula, dados, nota):
            v = 50. if valor is None else limitar(valor / 100) * 100
            ce = 0. if valor is None else confianca
            saida[codigo] = {'nome': self.config['coberturas'][codigo]['nome'],
                'prioridade': v, 'prioridade_min': v * ce,
                'prioridade_max': v + (1-ce)*(100-v), 'confianca': ce,
                'origem': 'HEURISTICA_PREFERENCIA', 'formula': formula, 'dados': dados,
                'justificativa': nota + ' Pontos de preferência; não estimam probabilidade de sinistro.'}

        bens = numero(r.get('bens_total_referencia'))
        incluir(INCENDIO, h['incendio_com_bens'] if bens is not None else h['incendio_sem_inventario'],
                .35 if bens is not None else 0., 'Pontos configurados conforme existência de inventário',
                {'bens_total_referencia': bens}, 'Inventário não comprova risco de incêndio.')
        tecnologia = numero(r.get('indice_dependencia_tecnologica'))
        campo = 'indice_dependencia_tecnologica'
        if tecnologia is None:
            tecnologia = numero(r.get('dependencia_digital_pct'))
            tecnologia = tecnologia / 100 if tecnologia is not None else None
            campo = 'dependencia_digital_pct'
        if tecnologia is not None and tecnologia > 1:
            tecnologia = None
        incluir(ELETRICO, h['base_eletrico'] + h['amplitude_eletrico']*tecnologia if tecnologia is not None else None,
                .35, 'base_eletrico + amplitude_eletrico × dependência tecnológica',
                {campo: r.get(campo)}, 'Dependência operacional não comprova falha elétrica.')
        aluguel = r.get('pagamento_aluguel_recorrente')
        incluir(ALUGUEL, h['aluguel_sim'] if aluguel == 'SIM' else h['aluguel_nao'] if aluguel == 'NAO' else None,
                .35, 'Pontos configurados conforme sinal de pagamento recorrente',
                {'pagamento_aluguel_recorrente': aluguel}, 'Sem pagamento não comprova imóvel próprio ou ausência de renda de aluguel.')
        sinais = [r.get('possui_termo_loja'), r.get('possui_termo_galeria')]
        presencial = True if 'SIM' in sinais else False if sinais == ['NAO','NAO'] else None
        incluir(TERCEIROS, h['terceiros_presencial'] if presencial else h['terceiros_sem_sinal'] if presencial is False else None,
                .3, 'Pontos configurados conforme sinais de loja/galeria',
                {'possui_termo_loja': sinais[0], 'possui_termo_galeria': sinais[1]}, 'Texto do cadastro é um sinal fraco de circulação de terceiros.')
        despesa = numero(r.get('despesa_fixa_mensal_estimada'))
        incluir(DESPESAS, h['base_despesas'] + h['amplitude_despesas']*despesa/(despesa+h['ancora_despesa_mensal']) if despesa is not None else None,
                .4, 'base_despesas + amplitude_despesas × despesa/(despesa + ancora_despesa_mensal)',
                {'despesa_fixa_mensal_estimada': despesa, 'ancora': h['ancora_despesa_mensal']},
                'Importância experimental da continuidade operacional; não é soma de perdas.')
        incluir(CIBER, 30 + 60*tecnologia if tecnologia is not None else None, .35,
                '30 + 60 × dependência tecnológica; preferência experimental',
                {campo: r.get(campo)}, 'Cobertura obrigatória na matriz do guia; dependência não mede ataque ou controles.')
        return {c: saida[c] for c in self.config['coberturas']}

    def calcular_pontuacoes(self, empresa_id, imovel_id):
        if self.base is None:
            raise ValueError('Carregue uma base para consultar por identificador.')
        return self.analisar_registro(self.base.registro(empresa_id, imovel_id))


def calcular_pontuacoes(empresa_id, imovel_id, base=None, config=None):
    return MotorPontuacao(base or carregar_base(), config).calcular_pontuacoes(empresa_id, imovel_id)
