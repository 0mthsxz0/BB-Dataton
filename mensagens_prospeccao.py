"""Roteiro por template, preenchido com a recomendação já calculada."""
from __future__ import annotations

import math
from string import Formatter

from ligacoes import criar_twiml

TEMPLATE_BASE = (
    "{saudacao} {apresentacao} Gostaria de conversar sobre a proteção da empresa "
    "{empresa}, que atua em {atividade}, em {cidade}. Nossa análise preliminar "
    "indicou o plano {plano} como sugestão para avaliação. {argumento} "
    "{ressalvas} Podemos agendar uma conversa para entender melhor suas necessidades?"
)


def texto(valor, padrao=""):
    if valor is None:
        return padrao
    valor = " ".join(str(valor).split())
    return padrao if valor.lower() in {"", "nan", "none", "<na>"} else valor


def variaveis_relatorio(registro, pontos, plano, *, contato="", colaborador="",
                       organizacao="", empresa=""):
    coberturas = set(plano.get("coberturas", []))
    selecionadas = sorted(
        [s for codigo, s in pontos.items() if codigo in coberturas and not s.get("adicional")],
        key=lambda s: (-float(s["prioridade"]), s["nome"]),
    )[:2]
    nomes = " e ".join(s["nome"].lower() for s in selecionadas)
    argumento = (f"Os pontos de atenção priorizados no relatório foram {nomes}."
                 if nomes else "Gostaríamos de confirmar as necessidades de proteção do estabelecimento.")
    ressalvas = "A sugestão depende da confirmação dos dados, de cotação e das condições de contratação."
    if not plano.get("recomendacao_estavel", True):
        ressalvas += " A indicação pode mudar após essa confirmação."
    if float(plano.get("confianca_geral", 0)) < .5:
        ressalvas += " Há informações incompletas que precisamos validar."
    identidade = texto(colaborador)
    equipe = texto(organizacao)
    apresentacao = (f"Meu nome é {identidade}" if identidade else "Este é um contato de apresentação")
    if equipe:
        apresentacao += f", da {equipe}"
    apresentacao += "."
    return {
        "saudacao": f"Olá, {texto(contato)}!" if texto(contato) else "Olá!",
        "apresentacao": apresentacao,
        "empresa": texto(empresa) or texto(registro.get("razao_social")) or
                   texto(registro.get("nome_fantasia")) or texto(registro.get("empresa_id"), "sua empresa"),
        "atividade": texto(registro.get("descricao_cnae")) or
                     texto(registro.get("grupo_atividade"), "atividade a confirmar").replace("_", " ").lower(),
        "cidade": texto(registro.get("municipio_real"), "localidade a confirmar"),
        "plano": {"ESSENCIAL": "Essencial", "PRATICO": "Prático", "TOTAL": "Total"}.get(
            plano.get("plano_recomendado"), texto(plano.get("plano_recomendado"), "a confirmar")),
        "coberturas_prioritarias": nomes or "necessidades a confirmar",
        "argumento": argumento,
        "justificativa": texto(plano.get("justificativa")),
        "ressalvas": ressalvas,
    }


def preencher_template(template, variaveis):
    if not template.strip() or len(template) > 5000:
        raise ValueError("O modelo deve ter entre 1 e 5000 caracteres.")
    for _, nome, formato, conversao in Formatter().parse(template):
        if nome is not None and (nome not in variaveis or formato or conversao):
            raise ValueError("Variável inválida no modelo. Use somente os nomes listados, entre chaves.")
    mensagem = template.format_map(variaveis)
    criar_twiml(mensagem)
    return mensagem


def json_seguro(valor):
    """Normaliza o relatório para download JSON estrito, sem NaN."""
    if isinstance(valor, dict):
        return {str(k): json_seguro(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [json_seguro(v) for v in valor]
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else None
    if valor is None or isinstance(valor, (str, bool, int)):
        return valor
    if hasattr(valor, "item"):
        return json_seguro(valor.item())
    return str(valor)
