"""Indicadores externos e cenários. Funções puras; rede somente no script de preparo."""
from datetime import date
import math
import re


def classe_cnae(valor):
    codigo = re.sub(r'\D', '', str(valor or ''))
    return codigo[:5] if len(codigo) in (5, 7) else None


def extrair_classes_nr4(conteudo):
    """Aceita descrições quebradas em várias linhas, sem atravessar outra classe."""
    padrao=r'(?m)^\s*(\d{2}\.\d{2}-\d)[ \t]+((?:(?!\n\s*\d{2}\.\d{2}-\d)[\s\S])*?)\s+([1-4])[ \t]*$'
    return [{'classe_cnae':classe_cnae(m[1]),'descricao_nr4':' '.join(m[2].split()),
             'grau_risco_nr4':int(m[3])} for m in re.finditer(padrao,conteudo)]


def indicador_climatico(daily, parametros):
    dias = daily.get('time', [])
    vento = daily.get('wind_gusts_10m_max', [])
    chuva = daily.get('precipitation_sum', [])
    if not dias or not len(dias) == len(vento) == len(chuva) or len(set(dias)) != len(dias):
        raise ValueError('Série climática vazia, duplicada ou com comprimentos divergentes.')
    datas = [date.fromisoformat(d) for d in dias]
    if datas != sorted(datas):
        raise ValueError('Datas climáticas fora de ordem.')
    esperado = (datas[-1] - datas[0]).days + 1
    def valido(v):
        return isinstance(v, (int, float)) and math.isfinite(v) and v >= 0
    fortes = severos = conjuntos = nv = nc = 0
    for v, c in zip(vento, chuva):
        if valido(v):
            nv += 1
            fortes += v >= parametros['rajada_forte_kmh']
            severos += v >= parametros['rajada_severa_kmh']
            if valido(c):
                nc += 1
                conjuntos += v >= parametros['rajada_chuva_kmh'] and c >= parametros['chuva_mm']
    if not nv or not nc:
        raise ValueError('Sem observações válidas suficientes para vento e chuva.')
    a, b, c = fortes/nv, severos/nv, conjuntos/nc
    pesos = parametros['pesos']
    bruto = pesos[0]*a + pesos[1]*b + pesos[2]*c
    ref = parametros['referencia_frequencia']
    return {'frequencia_rajada_forte': a, 'frequencia_rajada_severa': b,
            'frequencia_vento_chuva': c, 'exposicao_climatica_bruta': bruto,
            'exposicao_climatica_0_1': bruto/(bruto+ref),
            'dias_esperados': esperado, 'dias_vento_validos': nv, 'dias_conjuntos_validos': nc,
            'completude': min(nv, nc)/esperado}
