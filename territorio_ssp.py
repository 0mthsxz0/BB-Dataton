"""Importação de balanços criminais públicos das SSPs.

O módulo transforma planilhas estaduais/regionais em uma camada territorial
compatível com ``processamento.incorporar_territorio``. A fonte é tratada como
proxy de exposição relativa a roubo em comércio, nunca como probabilidade de
sinistro.

O formato de entrada é uma lista de registros com ``arquivo``, ``uf``,
``regiao`` e ``ano``. O código IBGE e o número de estabelecimentos são
opcionais, mas melhoram a junção e a normalização. A ausência do denominador é
registrada na metodologia e reduz a confiança do indicador.
"""
from __future__ import annotations

from pathlib import Path
import math
import re
import unicodedata

import numpy as np
import pandas as pd


MESES = ("JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ")
INDICADOR_ROUBO = "ROUBO EM COMERCIO"


def _texto(valor) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return ""
    texto = str(valor).strip().upper()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", texto)


def _numero(valor):
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return None
    try:
        numero = float(str(valor).replace(".", "").replace(",", "."))
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) and numero >= 0 else None


def _cabecalho(raw: pd.DataFrame):
    """Localiza a linha de cabeçalho em planilhas com título institucional."""
    for indice in range(len(raw)):
        valores = [_texto(v) for v in raw.iloc[indice].tolist()]
        if any("NATUREZA DO CRIME" in v for v in valores) and any(v == "TOTAL" for v in valores):
            natureza = next(i for i, v in enumerate(valores) if "NATUREZA DO CRIME" in v)
            total = next(i for i, v in enumerate(valores) if v == "TOTAL")
            meses = {v: i for i, v in enumerate(valores) if v in MESES}
            return indice, natureza, total, meses
    raise ValueError("Planilha SSP sem cabeçalho reconhecível de natureza e total.")


def ler_balanco_ssp(caminho, *, uf, regiao, ano, codigo_ibge_municipio=None,
                    fonte=None, estabelecimentos=None):
    """Lê uma planilha de balanço e extrai o indicador de roubo em comércio."""
    caminho = Path(caminho)
    raw = pd.read_excel(caminho, header=None)
    inicio, coluna_natureza, coluna_total, colunas_meses = _cabecalho(raw)
    encontrados = []
    for linha in range(inicio + 1, len(raw)):
        natureza = _texto(raw.iat[linha, coluna_natureza])
        if INDICADOR_ROUBO in natureza and not natureza.startswith("TOTAL"):
            total = _numero(raw.iat[linha, coluna_total])
            meses = {mes: _numero(raw.iat[linha, coluna]) for mes, coluna in colunas_meses.items()}
            observados = [valor for valor in meses.values() if valor is not None]
            encontrados.append((total, meses, observados, natureza))
    if not encontrados:
        raise ValueError(f"{caminho.name}: linha 'Roubo em Comércio' não encontrada.")
    total, meses, observados, natureza = encontrados[0]
    if total is None:
        total = sum(observados) if observados else None
    return {
        "arquivo": str(caminho),
        "uf": str(uf).upper(),
        "regiao_administrativa": str(regiao),
        "codigo_ibge_municipio": str(codigo_ibge_municipio or ""),
        "ano": str(ano),
        "natureza_fonte": natureza,
        "roubo_comercio_total": total,
        "meses_observados": len(observados),
        "media_mensal": (sum(observados) / len(observados)) if observados else None,
        "fonte": fonte or "SSP estadual; arquivo fornecido pela equipe",
        "estabelecimentos": _numero(estabelecimentos),
    }


def _normalizar(valores):
    """Normalização robusta entre unidades; retorna None quando não há contraste."""
    serie = pd.Series(valores, dtype="float64")
    validos = serie.dropna()
    if len(validos) < 2 or validos.max() == validos.min():
        return pd.Series([None] * len(serie), index=serie.index, dtype="object")
    baixo, alto = validos.quantile(.05), validos.quantile(.95)
    if alto <= baixo:
        baixo, alto = validos.min(), validos.max()
    resultado = ((serie - baixo) / (alto - baixo)).clip(0, 1)
    return resultado.where(serie.notna(), None)


def construir_enriquecimento(registros, *, ano_referencia=None):
    """Consolida registros e devolve o esquema aceito pelo motor.

    A unidade exportada é o município/IBGE. Regiões administrativas do mesmo
    município são agregadas, pois o dataset do Datathon só permite uma junção
    municipal segura. Para usar RA em produção, inclua uma chave de RA real no
    endereço e altere a junção para ``(codigo_ibge_municipio, regiao)``.
    """
    dados = pd.DataFrame(list(registros))
    obrigatorias = {"uf", "regiao_administrativa", "ano", "codigo_ibge_municipio", "roubo_comercio_total"}
    faltantes = obrigatorias - set(dados.columns)
    if faltantes:
        raise ValueError(f"Registros SSP sem colunas: {sorted(faltantes)}")
    dados["roubo_comercio_total"] = pd.to_numeric(dados["roubo_comercio_total"], errors="coerce")
    if "estabelecimentos" not in dados:
        dados["estabelecimentos"] = np.nan
    dados["estabelecimentos"] = pd.to_numeric(dados["estabelecimentos"], errors="coerce")
    dados["codigo_ibge_municipio"] = dados["codigo_ibge_municipio"].fillna("").astype(str)
    dados["codigo_ibge_municipio"] = dados["codigo_ibge_municipio"].replace({"nan": ""})

    # Sem código IBGE não há junção segura com a base do Datathon.
    dados = dados[dados["codigo_ibge_municipio"].str.strip().ne("")].copy()
    if dados.empty:
        raise ValueError("Nenhum registro SSP possui codigo_ibge_municipio para a junção.")

    # Quando há denominador, usa taxa por mil estabelecimentos; caso contrário,
    # mantém a contagem agregada e documenta a limitação.
    dados["taxa_por_mil_estabelecimentos"] = np.where(
        dados["estabelecimentos"].gt(0),
        dados["roubo_comercio_total"] / dados["estabelecimentos"] * 1000,
        np.nan,
    )
    chave = "taxa_por_mil_estabelecimentos" if dados["taxa_por_mil_estabelecimentos"].notna().any() else "roubo_comercio_total"
    municipio = dados.groupby("codigo_ibge_municipio", as_index=False).agg(
        uf=("uf", "first"),
        roubo_comercio_total=("roubo_comercio_total", "sum"),
        estabelecimentos=("estabelecimentos", "sum"),
        regioes_fonte=("regiao_administrativa", lambda s: "|".join(sorted(set(map(str, s))))),
        anos_fonte=("ano", lambda s: "|".join(sorted(set(map(str, s))))),
        taxa_referencia=(chave, "mean"),
    )
    exposicao = _normalizar(municipio["taxa_referencia"])
    municipio["exposicao_roubo_0_1"] = exposicao
    municipio["seguranca_da_cidade_0_1"] = municipio["exposicao_roubo_0_1"].map(
        lambda x: None if x is None or pd.isna(x) else 1 - float(x)
    )
    # Um único município (por exemplo, apenas o arquivo agregado do DF) não
    # permite ordenar exposição. Mantemos um prior neutro, com confiança zero,
    # para que o motor continue executável sem transformar ausência em proteção.
    sem_contraste = municipio["seguranca_da_cidade_0_1"].isna()
    municipio.loc[sem_contraste, "seguranca_da_cidade_0_1"] = .5
    municipio.loc[sem_contraste, "exposicao_roubo_0_1"] = .5
    com_denominador = chave != "roubo_comercio_total"
    cobertura_temporal = dados.groupby("codigo_ibge_municipio")["ano"].nunique().max() >= 2
    confianca = .55 if com_denominador and cobertura_temporal else (.40 if com_denominador else .25)
    if sem_contraste.any():
        confianca = 0.0
    metodologia = (
        "Roubo em Comércio normalizado por mil estabelecimentos; comparação relativa entre municípios."
        if com_denominador else
        "Contagem de Roubo em Comércio normalizada entre municípios; sem denominador de exposição."
    )
    if sem_contraste.any():
        metodologia += " Não há contraste territorial suficiente; valor neutro 0,5 e confiança zero."
    ano = ano_referencia or "|".join(sorted(set(dados["ano"].astype(str))))
    saida = pd.DataFrame({
        "codigo_ibge_municipio": municipio["codigo_ibge_municipio"],
        "seguranca_da_cidade_0_1": municipio["seguranca_da_cidade_0_1"],
        "exposicao_roubo_0_1": municipio["exposicao_roubo_0_1"],
        "fonte": "SSP estadual / Sinesp; arquivos: " + municipio["regioes_fonte"],
        "ano_referencia": ano,
        "granularidade": "MUNICIPIO",
        "metodologia": metodologia,
        "confianca_territorial_0_1": confianca,
        "roubo_comercio_total": municipio["roubo_comercio_total"],
        "regioes_fonte": municipio["regioes_fonte"],
        "observacao_territorial": "Proxy de exposição relativa; não é probabilidade de sinistro.",
    })
    return saida


def construir_de_manifesto(manifesto_csv, destino):
    """Lê um manifesto CSV e grava o enriquecimento municipal."""
    manifesto = pd.read_csv(manifesto_csv, dtype=str, keep_default_na=False)
    obrigatorias = {"arquivo", "uf", "regiao", "ano", "codigo_ibge_municipio"}
    faltantes = obrigatorias - set(manifesto.columns)
    if faltantes:
        raise ValueError(f"Manifesto SSP sem colunas: {sorted(faltantes)}")
    registros = []
    raiz = Path(manifesto_csv).resolve().parent
    for linha in manifesto.to_dict("records"):
        caminho = Path(linha["arquivo"])
        if not caminho.is_absolute():
            caminho = raiz / caminho
        registros.append(ler_balanco_ssp(
            caminho, uf=linha["uf"], regiao=linha["regiao"], ano=linha["ano"],
            codigo_ibge_municipio=linha["codigo_ibge_municipio"],
            fonte=linha.get("fonte") or None, estabelecimentos=linha.get("estabelecimentos") or None,
        ))
    resultado = construir_enriquecimento(registros)
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(destino, index=False, encoding="utf-8-sig")
    return resultado

