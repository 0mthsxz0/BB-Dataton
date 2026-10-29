"""SQLite com proveniência e importação estrita de séries mensais."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import sqlite3
import unicodedata

import pandas as pd


def normalizar(valor):
    texto = ''.join(c for c in unicodedata.normalize('NFKD', str(valor)).lower()
                    if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', texto).strip()


MESES = dict(zip(('janeiro fevereiro marco abril maio junho julho agosto setembro outubro novembro dezembro').split(), range(1, 13)))
UF_NOMES = dict(zip(map(normalizar, ['Acre', 'Alagoas', 'Amapá', 'Amazonas', 'Bahia', 'Ceará',
    'Distrito Federal', 'Espírito Santo', 'Goiás', 'Maranhão', 'Mato Grosso', 'Mato Grosso do Sul',
    'Minas Gerais', 'Pará', 'Paraíba', 'Paraná', 'Pernambuco', 'Piauí', 'Rio de Janeiro',
    'Rio Grande do Norte', 'Rio Grande do Sul', 'Rondônia', 'Roraima', 'Santa Catarina',
    'São Paulo', 'Sergipe', 'Tocantins']),
    'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split()))


def sigla_uf(valor):
    return UF_NOMES.get(normalizar(valor), str(valor).strip().upper())


CRIMES = {
    'roubo de veiculo': 'roubo de veiculos',
    'roubo de cargas': 'roubo de carga',
    'roubo a instituicoes financeiras': 'roubo a instituicao financeira',
    'latrocinio': 'roubo seguido de morte latrocinio',
    'roubo seguido de morte': 'roubo seguido de morte latrocinio',
}
COLUNAS = {
    'codigo': ['codigo ibge', 'cod ibge', 'codigo ibge municipio', 'codigo municipio', 'municipio codigo', 'ibge'],
    'municipio': ['municipio', 'nome municipio', 'municipio nome'],
    'uf': ['uf', 'sigla uf', 'unidade da federacao', 'estado'],
    'ano': ['ano', 'ano referencia'],
    'mes': ['mes', 'mes referencia'],
    'crime': ['crime', 'tipo crime', 'tipo de crime', 'natureza', 'indicador'],
    'ocorrencias': ['ocorrencias', 'total ocorrencias', 'quantidade ocorrencias', 'numero de ocorrencias'],
}


def crime_canonico(valor):
    chave = normalizar(valor)
    return CRIMES.get(chave, chave)


@contextmanager
def conectar(caminho, somente_leitura=False):
    caminho = Path(caminho).resolve()
    if somente_leitura:
        con = sqlite3.connect(caminho.as_uri() + '?mode=ro', uri=True)
    else:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(caminho)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
        if not somente_leitura:
            con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def inicializar(con):
    con.executescript('''
    CREATE TABLE IF NOT EXISTS fontes (
        id INTEGER PRIMARY KEY, url TEXT NOT NULL, arquivo TEXT NOT NULL,
        sha256 TEXT NOT NULL, coletado_em TEXT NOT NULL, metadados TEXT NOT NULL, UNIQUE(url,sha256));
    CREATE TABLE IF NOT EXISTS municipios (
        codigo_ibge TEXT PRIMARY KEY CHECK(length(codigo_ibge)=7 AND codigo_ibge NOT GLOB '*[^0-9]*'),
        municipio TEXT NOT NULL, uf TEXT NOT NULL CHECK(length(uf)=2),
        populacao REAL CHECK(populacao>0), area_km2 REAL CHECK(area_km2>0),
        ano_populacao INTEGER, ano_area INTEGER,
        fonte_id INTEGER NOT NULL REFERENCES fontes(id));
    CREATE TABLE IF NOT EXISTS ocorrencias (
        codigo_ibge TEXT NOT NULL REFERENCES municipios(codigo_ibge),
        crime TEXT NOT NULL, mes TEXT NOT NULL,
        ocorrencias INTEGER NOT NULL CHECK(ocorrencias>=0),
        PRIMARY KEY(codigo_ibge,crime,mes));
    CREATE INDEX IF NOT EXISTS ocorrencias_periodo ON ocorrencias(mes,crime);
    CREATE TABLE IF NOT EXISTS ocorrencia_fontes (
        codigo_ibge TEXT NOT NULL, crime TEXT NOT NULL, mes TEXT NOT NULL,
        fonte_id INTEGER NOT NULL REFERENCES fontes(id),
        PRIMARY KEY(codigo_ibge,crime,mes,fonte_id),
        FOREIGN KEY(codigo_ibge,crime,mes) REFERENCES ocorrencias(codigo_ibge,crime,mes));
    CREATE TABLE IF NOT EXISTS rejeicoes (
        fonte_id INTEGER NOT NULL REFERENCES fontes(id), folha TEXT NOT NULL,
        linha INTEGER NOT NULL, motivo TEXT NOT NULL, dados TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS execucoes (
        id INTEGER PRIMARY KEY, criado_em TEXT NOT NULL, parametros TEXT NOT NULL,
        diagnostico TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS indices (
        codigo_ibge TEXT PRIMARY KEY REFERENCES municipios(codigo_ibge),
        indice_roubo_0_100 REAL CHECK(indice_roubo_0_100 BETWEEN 0 AND 100),
        faixa TEXT NOT NULL, confianca TEXT NOT NULL, completude_0_1 REAL NOT NULL,
        inicio TEXT NOT NULL, fim TEXT NOT NULL, detalhes TEXT NOT NULL,
        execucao_id INTEGER NOT NULL REFERENCES execucoes(id));
    CREATE VIEW IF NOT EXISTS consulta_municipal AS
        SELECT m.*, m.populacao/m.area_km2 AS densidade_hab_km2,
        i.indice_roubo_0_100,i.faixa,i.confianca,i.completude_0_1,i.inicio,i.fim,i.detalhes
        FROM municipios m LEFT JOIN indices i USING(codigo_ibge);
    ''')


def registrar_fonte(con, arquivo, url, metadados=None):
    arquivo = Path(arquivo)
    with arquivo.open('rb') as entrada:
        digest = hashlib.file_digest(entrada, 'sha256').hexdigest()
    coletado_em = datetime.now(timezone.utc).isoformat()
    sidecar = arquivo.with_name(arquivo.name+'.fonte.json')
    if sidecar.exists():
        coleta = json.loads(sidecar.read_text(encoding='utf-8'))
        if coleta['url'] != url or coleta['sha256'] != digest:
            raise ValueError('Metadados de coleta não correspondem ao arquivo/fonte.')
        if datetime.fromisoformat(coleta['coletado_em']).tzinfo is None:
            raise ValueError('Data de coleta sem fuso horário.')
        coletado_em = coleta['coletado_em']
    con.execute('INSERT OR IGNORE INTO fontes(url,arquivo,sha256,coletado_em,metadados) VALUES(?,?,?,?,?)',
                (url, str(arquivo.resolve()), digest, coletado_em,
                 json.dumps(metadados or {}, ensure_ascii=False)))
    fonte = con.execute('SELECT id FROM fontes WHERE url=? AND sha256=?', (url, digest)).fetchone()[0]
    if sidecar.exists():
        con.execute('UPDATE fontes SET coletado_em=? WHERE id=?', (coletado_em, fonte))
    return fonte


def numero(valor, inteiro=False):
    texto = str(valor).strip()
    if texto in ('', '-', '...', '..', 'X', 'x', 'nan', 'None'):
        return None
    # IBGE usa ponto decimal; CSV brasileiro pode ter vírgula decimal.
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    v = float(texto)
    if not pd.notna(v) or v == float('inf') or v < 0 or (inteiro and not v.is_integer()):
        raise ValueError(f'Número inválido: {valor!r}')
    return int(v) if inteiro else v


def importar_ibge(con, localidades, indicadores, url_localidades, url_indicadores, ano=2022):
    """Respostas oficiais: localidades/municipios e agregado 4714 (93 e 6318)."""
    con.execute('DELETE FROM indices')
    localidades, indicadores = Path(localidades), Path(indicadores)
    lista = json.loads(localidades.read_text(encoding='utf-8'))
    dados = json.loads(indicadores.read_text(encoding='utf-8'))
    valores = {}
    for variavel in dados:
        chave = {'93': 'populacao', '6318': 'area_km2'}.get(str(variavel['id']))
        if chave is None:
            continue
        unidade = normalizar(variavel.get('unidade', ''))
        if unidade and ((chave == 'populacao' and unidade != 'pessoas')
                        or (chave == 'area_km2' and unidade not in ('quilometros quadrados', 'km2'))):
            raise ValueError(f'IBGE: unidade inesperada para {chave}: {unidade}')
        if len(variavel['resultados']) != 1:
            raise ValueError('IBGE: categorias inesperadas; conferir o agregado 4714.')
        for serie in variavel['resultados'][0]['series']:
            codigo = str(serie['localidade']['id'])
            v = numero(serie['serie'].get(str(ano)))
            if v is not None and v <= 0:
                raise ValueError(f'IBGE: {chave} não positivo para {codigo}')
            valores.setdefault(codigo, {})[chave] = v
    if not valores or not any('area_km2' in v for v in valores.values()):
        raise ValueError('IBGE sem população/área esperadas; não importar resposta de erro.')
    # Duas fontes ficam registradas; o vínculo de indicadores é explícito nos metadados.
    loc_id = registrar_fonte(con, localidades, url_localidades)
    fonte = registrar_fonte(con, indicadores, url_indicadores, {'ano': ano, 'localidades_fonte_id': loc_id})
    vistos = set()
    for local in lista:
        codigo = str(local['id'])
        if codigo in vistos:
            raise ValueError(f'Município duplicado no IBGE: {codigo}')
        vistos.add(codigo)
        regiao = local.get('regiao-imediata')
        uf = (regiao['regiao-intermediaria']['UF'] if regiao else local['microrregiao']['mesorregiao']['UF'])['sigla']
        v = valores.get(codigo, {})
        con.execute('''INSERT INTO municipios VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(codigo_ibge) DO UPDATE SET municipio=excluded.municipio,uf=excluded.uf,
            populacao=excluded.populacao,area_km2=excluded.area_km2,ano_populacao=excluded.ano_populacao,
            ano_area=excluded.ano_area,fonte_id=excluded.fonte_id''',
            (codigo, local['nome'], uf, v.get('populacao'), v.get('area_km2'),
             ano if v.get('populacao') else None, ano if v.get('area_km2') else None, fonte))
    return len(vistos)


def importar_populacao(con, arquivo, url, ano):
    """Estimativa IBGE 6579/9324; atualiza população sem mudar a área censitária."""
    dados = json.loads(Path(arquivo).read_text(encoding='utf-8'))
    if (len(dados) != 1 or str(dados[0]['id']) != '9324'
            or normalizar(dados[0]['unidade']) != 'pessoas'
            or len(dados[0]['resultados']) != 1):
        raise ValueError('Estimativa IBGE: variável, unidade ou categorias inesperadas.')
    series = dados[0]['resultados'][0]['series']
    valores = {}
    for s in series:
        codigo = str(s['localidade']['id'])
        if codigo in valores or not re.fullmatch(r'\d{7}', codigo):
            raise ValueError('Estimativa IBGE: código duplicado ou inválido.')
        valor = numero(s['serie'].get(str(ano)), inteiro=True)
        if valor is None or valor <= 0:
            raise ValueError('Estimativa IBGE: população ausente ou não positiva.')
        valores[codigo] = valor
    cadastro = {r[0] for r in con.execute('SELECT codigo_ibge FROM municipios')}
    if set(valores) != cadastro:
        raise ValueError('Estimativa e cadastro têm códigos diferentes; revisar compatibilidade territorial.')
    fonte = registrar_fonte(con, arquivo, url, {'ano': ano, 'variavel': '9324'})
    # Mantém o vínculo censitário da área; o vínculo da estimativa é registrado na fonte.
    con.execute('DELETE FROM indices')
    con.executemany('UPDATE municipios SET populacao=?,ano_populacao=? WHERE codigo_ibge=?',
                    [(v, ano, c) for c, v in valores.items()])
    return {'municipios': len(valores), 'ano_populacao': ano, 'fonte_id': fonte}


def identificar_colunas(colunas, mapa=None):
    normalizadas = {normalizar(c): c for c in colunas}
    if len(normalizadas) != len(colunas):
        raise ValueError('Cabeçalhos duplicados após normalização.')
    resultado = {}
    for chave, aliases in COLUNAS.items():
        if mapa and chave in mapa:
            if mapa[chave] not in colunas:
                raise ValueError(f'Coluna configurada não existe: {mapa[chave]}')
            resultado[chave] = mapa[chave]
        else:
            encontradas = [normalizadas[a] for a in aliases if a in normalizadas]
            if len(encontradas) > 1:
                raise ValueError(f'Colunas ambíguas para {chave}: {encontradas}; forneça --mapa.')
            if encontradas:
                resultado[chave] = encontradas[0]
    mensais = {nome: MESES[normalizar(nome)] for nome in colunas if normalizar(nome) in MESES}
    if 'ano' not in resultado or 'crime' not in resultado:
        raise ValueError('Faltam ano e natureza/tipo de crime. Totais estaduais não são dados municipais.')
    if 'codigo' not in resultado and not {'municipio', 'uf'} <= resultado.keys():
        raise ValueError('Falta código IBGE ou par município/UF; não inferir município pelo nome isolado.')
    if not mensais and not {'mes', 'ocorrencias'} <= resultado.keys():
        raise ValueError('Faltam mês/ocorrências ou colunas mensais; vítimas não substituem ocorrências.')
    return resultado, mensais


def tabelas(arquivo, mapa=None):
    """Detecta cabeçalho até a linha 20; só importa folhas com esquema municipal."""
    arquivo = Path(arquivo)
    if arquivo.suffix.lower() == '.csv':
        erro = None
        for encoding in ('utf-8-sig', 'cp1252'):
            try:
                yield arquivo.name, pd.read_csv(arquivo, sep=None, engine='python', dtype=str,
                                                keep_default_na=False, encoding=encoding), 2
                return
            except UnicodeDecodeError as exc:
                erro = exc
        raise erro
    if arquivo.suffix.lower() not in ('.xls', '.xlsx'):
        raise ValueError('Importe arquivos CSV/XLS/XLSX; ZIPs devem ser inspecionados antes.')
    folhas = pd.read_excel(arquivo, sheet_name=None, header=None, dtype=str, keep_default_na=False)
    ignoradas = []
    validas = []
    for nome, bruto in folhas.items():
        for i in range(min(20, len(bruto))):
            cab = bruto.iloc[i].astype(str).tolist()
            try:
                identificar_colunas(cab, mapa)
            except ValueError:
                continue
            df = bruto.iloc[i+1:].copy()
            df.columns = cab
            validas.append((nome, df, i+2))
            break
        else:
            ignoradas.append(nome)
    if not validas:
        raise ValueError(f'Nenhuma folha municipal reconhecida em {arquivo.name}: {ignoradas}')
    # Folhas não tabulares são inventariadas, nunca apresentadas como importadas.
    yield from validas


def importar_sinesp(con, arquivo, url, mapa=None):
    if not con.execute('SELECT 1 FROM municipios LIMIT 1').fetchone():
        raise ValueError('Importe primeiro o cadastro e os denominadores do IBGE.')
    con.execute('DELETE FROM indices')
    fonte = registrar_fonte(con, arquivo, url)
    # Uma nova importação idêntica refaz somente o diagnóstico da mesma fonte.
    con.execute('DELETE FROM rejeicoes WHERE fonte_id=?', (fonte,))
    por_codigo = {r['codigo_ibge']: dict(r) for r in con.execute('SELECT * FROM municipios')}
    por_nome = {}
    for r in por_codigo.values():
        por_nome.setdefault((normalizar(r['municipio']), r['uf']), []).append(r['codigo_ibge'])
    folhas_arquivo = pd.ExcelFile(arquivo).sheet_names if Path(arquivo).suffix.lower() in ('.xls', '.xlsx') else [Path(arquivo).name]
    contagem = {'observacoes': 0, 'rejeicoes': 0, 'ausentes': 0, 'folhas': [], 'folhas_ignoradas': []}
    chaves_arquivo = set()
    for folha, df, primeira in tabelas(arquivo, mapa):
        cols, meses = identificar_colunas(list(df.columns), mapa)
        contagem['folhas'].append({'nome': folha, 'linhas': len(df), 'colunas': list(df.columns)})
        for linha, valores in enumerate(df.to_dict('records'), primeira):
            if not any(str(v).strip() for v in valores.values()):
                continue
            try:
                codigo = str(valores.get(cols.get('codigo'), '')).strip().removesuffix('.0')
                if not codigo:
                    chave = (normalizar(valores[cols['municipio']]), sigla_uf(valores[cols['uf']]))
                    candidatos = por_nome.get(chave, [])
                    if len(candidatos) != 1:
                        raise ValueError('Município/UF sem correspondência unívoca no IBGE')
                    codigo = candidatos[0]
                if codigo not in por_codigo:
                    raise ValueError('Código municipal ausente do cadastro IBGE')
                if 'uf' in cols and sigla_uf(valores[cols['uf']]) != por_codigo[codigo]['uf']:
                    raise ValueError('UF divergente do código IBGE (use sigla de duas letras)')
                if 'municipio' in cols and normalizar(valores[cols['municipio']]) != normalizar(por_codigo[codigo]['municipio']):
                    raise ValueError('Nome municipal divergente do código IBGE; revisar alteração territorial')
                ano = numero(valores[cols['ano']], inteiro=True)
                if ano is None or not 2000 <= ano <= datetime.now().year:
                    raise ValueError('Ano fora do intervalo suportado')
                crime = crime_canonico(valores[cols['crime']])
                if not crime:
                    raise ValueError('Tipo de crime vazio')
                if meses:
                    observacoes = [(m, valores[col]) for col, m in meses.items()]
                else:
                    texto_mes = normalizar(valores[cols['mes']])
                    mes = MESES.get(texto_mes)
                    if mes is None:
                        mes = numero(texto_mes, inteiro=True)
                    observacoes = [(mes, valores[cols['ocorrencias']])]
                preparadas = []
                for mes, valor in observacoes:
                    if mes is None or not 1 <= mes <= 12:
                        raise ValueError('Mês inválido')
                    periodo = f'{ano:04d}-{mes:02d}-01'
                    if periodo >= datetime.now(timezone.utc).strftime('%Y-%m-01'):
                        raise ValueError('Mês corrente ou futuro: não é um mês fechado')
                    n = numero(valor, inteiro=True)
                    if n is None:
                        contagem['ausentes'] += 1
                        continue
                    chave = (codigo, crime, periodo)
                    if chave in chaves_arquivo:
                        raise RuntimeError(f'Chave mensal repetida no mesmo arquivo: {chave}; não somar dimensões desconhecidas')
                    existente = con.execute('SELECT ocorrencias FROM ocorrencias WHERE codigo_ibge=? AND crime=? AND mes=?', chave).fetchone()
                    if existente and existente[0] != n:
                        raise RuntimeError(f'Fontes conflitantes para {chave}: {existente[0]} e {n}. Revisão manual necessária.')
                    preparadas.append((chave, n))
            except (ValueError, KeyError) as exc:
                con.execute('INSERT INTO rejeicoes VALUES(?,?,?,?,?)',
                            (fonte, folha, linha, str(exc), json.dumps(valores, ensure_ascii=False)))
                contagem['rejeicoes'] += 1
                continue
            for chave, n in preparadas:
                chaves_arquivo.add(chave)
                con.execute('INSERT OR IGNORE INTO ocorrencias VALUES(?,?,?,?)', (*chave, n))
                con.execute('INSERT OR IGNORE INTO ocorrencia_fontes VALUES(?,?,?,?)', (*chave, fonte))
                contagem['observacoes'] += 1
    if contagem['observacoes'] == 0 and contagem['rejeicoes'] == 0:
        raise ValueError('Nenhuma observação municipal importável; confira o esquema e os dados.')
    contagem['folhas_ignoradas'] = sorted(set(folhas_arquivo)-{f['nome'] for f in contagem['folhas']})
    con.execute('UPDATE fontes SET metadados=? WHERE id=?', (json.dumps({'origem_dados': 'SINESP', **contagem}, ensure_ascii=False), fonte))
    return contagem
