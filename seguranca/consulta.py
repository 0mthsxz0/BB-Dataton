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
            dados['hierarquia_fontes'] = []
            if con.execute('SELECT 1 FROM sqlite_master WHERE name=?', ('hierarquia_selecao',)).fetchone():
                for h in con.execute('''SELECT h.*,f.url,f.sha256 FROM hierarquia_selecao h
                    LEFT JOIN fontes f ON f.id=h.fonte_id WHERE h.codigo_ibge=? ORDER BY h.crime''', (codigo,)):
                    fonte = dict(h)
                    fonte.pop('codigo_ibge')
                    fonte['tentativas'] = json.loads(fonte['tentativas'])
                    fonte['ocorrencias_12m'] = (con.execute('''SELECT sum(ocorrencias) FROM ocorrencias
                        WHERE codigo_ibge=? AND crime=? AND mes BETWEEN ? AND ?''',
                        (codigo, h['crime'], h['inicio']+'-01', h['fim']+'-01')).fetchone()[0]
                        if h['status'] == 'selecionada' else None)
                    dados['hierarquia_fontes'].append(fonte)
            dados['aviso'] = 'Contexto dos indicadores municipais selecionados. Mesmo roubo em comércio observado não é probabilidade individual de roubo nem previsão de sinistro.'
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
