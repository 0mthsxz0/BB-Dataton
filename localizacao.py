"""CEP localiza o município; não fornece um índice de risco de rua."""
from datetime import datetime, timezone
import re

import pandas as pd
import requests
from seguranca import avaliar_seguranca

from processamento import incorporar_indicador, incorporar_ssp, incorporar_territorio, ler_csv, localizar_referencias, caminho_referencia


def normalizar_cep(valor):
    texto = str(valor).strip()
    if not re.fullmatch(r'[0-9]{5}-?[0-9]{3}', texto):
        raise ValueError('Informe um CEP com oito dígitos, como 01001-000.')
    return texto.replace('-', '')


def consultar_cep(cep):
    cep = normalizar_cep(cep)
    url = f'https://viacep.com.br/ws/{cep}/json/'
    try:
        resposta = requests.get(url, timeout=(4, 10))
        resposta.raise_for_status()
        dados = resposta.json()
    except (requests.RequestException, ValueError) as erro:
        raise ValueError('Não foi possível consultar o CEP. Tente novamente mais tarde.') from erro
    if not isinstance(dados, dict):
        raise ValueError('O serviço de CEP retornou uma resposta inválida.')
    if dados.get('erro'):
        raise ValueError('CEP não encontrado. Confira os oito dígitos.')
    if (not re.fullmatch(r'[0-9]{7}', str(dados.get('ibge', '')))
            or not re.fullmatch(r'[A-Z]{2}', str(dados.get('uf', '')))
            or not str(dados.get('localidade', '')).strip()
            or normalizar_cep(dados.get('cep', '')) != cep):
        raise ValueError('O serviço retornou uma localização incompleta ou divergente.')
    return {
        'cep': cep, 'codigo_ibge_municipio': dados['ibge'],
        'municipio_real': dados['localidade'], 'uf_real': dados['uf'],
        'bairro': dados.get('bairro') or '', 'logradouro': dados.get('logradouro') or '',
        'fonte_localizacao': url,
        'consultado_em_utc': datetime.now(timezone.utc).isoformat(),
        'abrangencia_indicadores': 'MUNICIPIO',
    }


def aplicar_localizacao(registro, localizacao, referencias=None, enriquecimento=None):
    """Cópia para consulta: substitui indicadores e remove referências da cidade anterior."""
    novo = dict(registro)
    # Limpa também os metadados de referências legadas, evitando herdar fontes/confiança.
    for campo in list(novo):
        if (any(termo in campo for termo in ('seguranca', 'clima', 'rajada', 'vento_chuva'))
                or campo in {'fonte', 'ano_referencia', 'granularidade', 'metodologia',
                             'confianca_territorial_0_1', 'taxa_furto_domicilios',
                             'taxa_roubo_domicilios', 'exposicao_bruta', 'territorio_id',
                             'dias_esperados', 'dias_vento_validos', 'dias_conjuntos_validos',
                             'completude', 'latitude_publica', 'longitude_publica',
                             'latitude_celula', 'longitude_celula', 'sha256_serie'}):
            novo.pop(campo)
    for campo in ['indicador_disponivel','roubo_comercio_total','estabelecimentos_referencia',
                  'taxa_por_mil_estabelecimentos','referencia_taxa_por_mil','regioes_fonte',
                  'sha256_arquivos','atualizado_em_utc']:
        novo.pop(campo, None)
    for campo in ['fonte_denominador','ano_denominador','meses_observados_seguranca',
                  'cobertura_municipal_completa','tipo_seguranca']:
        novo.pop(campo, None)
    novo.pop('categoria_seguranca', None)
    novo.update(localizacao)
    dados = pd.DataFrame([novo])
    for tipo, indicador in [('seguranca', 'seguranca_da_cidade_0_1'),
                            ('clima', 'exposicao_climatica_0_1')]:
        caminho = caminho_referencia(f'{tipo}_municipal.csv',referencias)
        if caminho.exists():
            # Retira todos os campos da edição da referência antes de fazer o novo vínculo.
            colunas = set(ler_csv(caminho).columns) - {'codigo_ibge_municipio', 'municipio'}
            dados = dados.drop(columns=list(colunas), errors='ignore')
            dados = incorporar_indicador(dados, caminho, tipo)
    ssp = localizar_referencias(referencias)/'seguranca_ssp.csv'
    if ssp.exists():
        dados = incorporar_ssp(dados,ssp)
    if enriquecimento:
        dados = incorporar_territorio(dados,enriquecimento)
    avisos = []
    for tipo, indicador in [('seguranca','seguranca_da_cidade_0_1'),('clima','exposicao_climatica_0_1')]:
        if (indicador not in dados or pd.isna(dados.iloc[0][indicador])
                or tipo == 'seguranca' and dados.iloc[0].get('indicador_disponivel') == 'NAO'):
            avisos.append(f'Sem referência de {tipo} para este município; o risco permanece desconhecido.')
    resultado = dados.astype(object).where(pd.notna(dados), None).iloc[0].to_dict()
    qualidade = avaliar_seguranca(resultado)
    if not qualidade['utilizavel'] and not any('Sem referência de seguranca' in a for a in avisos):
        avisos.append('Segurança empresarial: ' + ' '.join(qualidade['motivos']))
    return resultado, avisos
