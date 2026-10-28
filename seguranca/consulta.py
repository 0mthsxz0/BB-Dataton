"""Consultas somente leitura; não cria um banco vazio ao consultar caminho errado."""
import json
import re

from .banco import conectar, normalizar


def consultar(caminho, codigo=None, uf=None, busca='', limite=100):
    with conectar(caminho, somente_leitura=True) as con:
        if not con.execute('SELECT 1 FROM municipios LIMIT 1').fetchone():
            return {'status': 503, 'erro': 'Base municipal ainda não importada; índice indisponível.'}
        if codigo is not None:
            if not re.fullmatch(r'\d{7}', codigo):
                return {'status': 400, 'erro': 'Informe código IBGE de sete dígitos.'}
            r = con.execute('SELECT * FROM consulta_municipal WHERE codigo_ibge=?', (codigo,)).fetchone()
            if r is None:
                return {'status': 404, 'erro': 'Município não encontrado no cadastro importado.'}
            dados = dict(r)
            dados.pop('fonte_id')
            dados['detalhes'] = json.loads(dados['detalhes']) if dados['detalhes'] else {'motivos': ['indice_nao_calculado']}
            execucao = con.execute('SELECT diagnostico FROM execucoes ORDER BY id DESC LIMIT 1').fetchone()
            metodo = json.loads(execucao[0]) if execucao else {}
            dados['pesos_critic'] = metodo.get('pesos_critic', {})
            dados['alertas'] = metodo.get('alertas', [])
            dados['escopo'] = 'contexto_municipal_de_roubos'
            dados['uso_empresarial_validado'] = False
            dados['crimes_indice'] = metodo.get('crimes', [])
            dados['fontes'] = [dict(f) for f in con.execute('SELECT DISTINCT url,sha256,coletado_em FROM fontes ORDER BY id')]
            dados['aviso'] = 'Contexto dos tipos de roubo disponíveis, sem roubo em comércio. Não mede probabilidade de roubo de estabelecimento nem previsão de sinistro.'
            return {'status': 200, 'dados': dados}
        if uf is None or not re.fullmatch(r'[A-Z]{2}', uf):
            return {'status': 400, 'erro': 'Informe a sigla da UF.'}
        if len(busca) > 100 or not 1 <= limite <= 6000:
            return {'status': 400, 'erro': 'Parâmetros de busca inválidos.'}
        candidatos = [dict(r) for r in con.execute(
            'SELECT codigo_ibge,municipio,uf FROM municipios WHERE uf=? ORDER BY municipio', (uf,))]
        texto = normalizar(busca)
        resultado = [r for r in candidatos if texto in normalizar(r['municipio']) or busca == r['codigo_ibge']]
        return {'status': 200, 'dados': {'municipios': resultado[:limite], 'total': len(resultado)}}
