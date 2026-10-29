"""python -m seguranca --help"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import pandas as pd

from .banco import conectar, inicializar, importar_ibge, importar_populacao, importar_sinesp, tabelas
from .consulta import consultar
from .fontes import coletar_ibge, coletar_sinesp, LOCALIDADES, INDICADORES
from .indice import gerar_indice
from .vde import importar_vde
from .auditoria import auditar
from .hierarquia import atualizar_hierarquia
from .mosler import avaliar_cruzamento
from .motor_principal import importar_referencia, consultar_motor, exportar_motor


RAIZ = Path(__file__).resolve().parents[1]


def emitir(dados):
    print(json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False))


def main():
    parser = argparse.ArgumentParser(description='Base municipal SINESP + IBGE e índice relativo de roubo.')
    parser.add_argument('--banco', type=Path, default=RAIZ/'data/seguranca/seguranca.sqlite')
    sub = parser.add_subparsers(dest='comando', required=True)
    sub.add_parser('iniciar', help='Cria somente o esquema; não contém dados de demonstração.')
    baixar = sub.add_parser('baixar', help='Baixa e inventaria arquivos oficiais sem importá-los automaticamente.')
    baixar.add_argument('--destino', type=Path, default=RAIZ/'data/seguranca/fontes')
    baixar.add_argument('--pagina-sinesp', default=None)
    baixar.add_argument('--atualizar', action='store_true')
    inspecionar = sub.add_parser('inspecionar')
    inspecionar.add_argument('arquivo', type=Path)
    ibge = sub.add_parser('importar-ibge')
    ibge.add_argument('--localidades', type=Path, required=True)
    ibge.add_argument('--indicadores', type=Path, required=True)
    populacao = sub.add_parser('importar-populacao')
    populacao.add_argument('arquivo', type=Path)
    populacao.add_argument('--url', required=True)
    populacao.add_argument('--ano', required=True, type=int)
    vde = sub.add_parser('importar-vde', help='Preserva escopo e unidade do VDE anual, sem rateio municipal.')
    vde.add_argument('arquivo', type=Path)
    vde.add_argument('--url', required=True)
    vde.add_argument('--auditoria', type=Path, required=True)
    vde.add_argument('--somente-bruto', action='store_true', help='Preserva registros sem publicar ocorrências municipais; permite coleta antes do cadastro IBGE.')
    importar_motor = sub.add_parser('importar-referencia-motor', help='Importa referência pública revisada compatível com a main; não aceita CSVs de clientes.')
    importar_motor.add_argument('arquivo', type=Path)
    importar_motor.add_argument('--data-analise')
    consultar_ref = sub.add_parser('consultar-motor', help='Consulta apenas referências elegíveis no contrato da main.')
    consultar_ref.add_argument('--codigo')
    consultar_ref.add_argument('--data-analise')
    exportar_ref = sub.add_parser('exportar-motor', help='Exporta CSV e manifesto para o motor da main, ou diagnóstico de pendências.')
    exportar_ref.add_argument('--saida', type=Path, required=True)
    exportar_ref.add_argument('--data-analise')
    sinesp = sub.add_parser('importar-sinesp')
    sinesp.add_argument('arquivo', type=Path)
    sinesp.add_argument('--url', required=True, help='URL original oficial do arquivo para proveniência.')
    sinesp.add_argument('--mapa', type=Path, help='JSON com aliases explícitos: codigo,municipio,uf,ano,mes,crime,ocorrencias.')
    indice = sub.add_parser('gerar-indice', help='Modelo municipal CRITIC anterior; não calcula Mosler por estabelecimento.')
    indice.add_argument('--config', type=Path, default=RAIZ/'config/seguranca.json')
    indice.add_argument('--fim', help='Último mês fechado, AAAA-MM; omitir usa o último publicado.')
    indice.add_argument('--saida', type=Path, default=RAIZ/'data/seguranca/exportacao')
    mosler = sub.add_parser('avaliar-mosler', help='Cruza IBGE, SINESP e CSV e calcula Mosler por estabelecimento.')
    mosler.add_argument('--estabelecimentos', type=Path, required=True, help='CSV consolidado, com chaves e avaliações Mosler documentadas.')
    mosler.add_argument('--config', type=Path, default=RAIZ/'config/seguranca_mosler.json')
    mosler.add_argument('--fim', required=True, help='Último mês civil encerrado da janela comum, AAAA-MM.')
    mosler.add_argument('--data-analise', help='AAAA-MM-DD; padrão America/Sao_Paulo.')
    mosler.add_argument('--saida', type=Path, default=RAIZ/'data/seguranca/mosler')
    consulta = sub.add_parser('consultar')
    consulta.add_argument('--codigo')
    consulta.add_argument('--uf')
    consulta.add_argument('--busca', default='')
    consulta.add_argument('--limite', type=int, default=100)
    sub.add_parser('resumo')
    auditoria = sub.add_parser('auditar')
    auditoria.add_argument('--estabelecimentos', required=True, type=Path)
    auditoria.add_argument('--saida', required=True, type=Path)
    hierarquia = sub.add_parser('resolver-fontes', help='Percorre fontes revisadas e seleciona séries municipais completas.')
    hierarquia.add_argument('--politica', type=Path, default=RAIZ/'config/fontes_seguranca.json')
    hierarquia.add_argument('--fontes', type=Path, default=RAIZ/'data/seguranca/fontes')
    hierarquia.add_argument('--fim', required=True)
    hierarquia.add_argument('--saida', type=Path, default=RAIZ/'data/seguranca/hierarquia')
    hierarquia.add_argument('--atualizar', action='store_true')
    args = parser.parse_args()
    if args.comando == 'baixar':
        resultado = {}
        try:
            resultado['ibge'] = coletar_ibge(args.destino/'ibge', args.atualizar)
        except Exception as exc:
            resultado['ibge_erro'] = str(exc)
        kw = {'pagina': args.pagina_sinesp} if args.pagina_sinesp else {}
        resultado['sinesp'] = coletar_sinesp(args.destino/'sinesp', atualizar=args.atualizar, **kw)
        emitir(resultado)
        return 2 if resultado.get('ibge_erro') or resultado['sinesp']['falhas'] or not resultado['sinesp']['baixados'] or resultado['sinesp']['limite_paginas_atingido'] else 0
    if args.comando == 'inspecionar':
        emitir([{'folha': nome, 'colunas': list(df.columns), 'linhas': len(df),
                 'amostra': df.head(5).to_dict('records')} for nome, df, _ in tabelas(args.arquivo)])
        return 0
    if args.comando in ('consultar-motor', 'exportar-motor'):
        with conectar(args.banco, somente_leitura=True) as con:
            resultado = (consultar_motor(con, args.codigo, args.data_analise)
                         if args.comando == 'consultar-motor' else
                         exportar_motor(con, args.saida, args.data_analise))
        emitir(resultado)
        return 0 if resultado['municipios_utilizaveis'] else 2
    if args.comando == 'auditar':
        with conectar(args.banco, somente_leitura=True) as con:
            emitir(auditar(con, args.estabelecimentos, args.saida))
        return 0
    if args.comando == 'consultar':
        try:
            r = consultar(args.banco, codigo=args.codigo, uf=args.uf, busca=args.busca, limite=args.limite)
        except (OSError, sqlite3.Error) as exc:
            r = {'status': 503, 'erro': 'Base de segurança indisponível. Execute a coleta e a importação.', 'tipo': type(exc).__name__}
        emitir(r)
        return 0 if r['status'] == 200 else 2
    if args.comando == 'resumo':
        with conectar(args.banco, somente_leitura=True) as con:
            emitir({'municipios': con.execute('SELECT count(*) FROM municipios').fetchone()[0],
                    'observacoes': con.execute('SELECT count(*) FROM ocorrencias').fetchone()[0],
                    'crimes': [dict(r) for r in con.execute('SELECT crime,min(mes) inicio,max(mes) fim,count(*) linhas FROM ocorrencias GROUP BY crime')],
                    'rejeicoes': con.execute('SELECT count(*) FROM rejeicoes').fetchone()[0],
                    'indices': con.execute('SELECT count(*) FROM indices WHERE indice_roubo_0_100 IS NOT NULL').fetchone()[0]})
        return 0
    if args.comando == 'avaliar-mosler':
        config = json.loads(args.config.read_text())
        with conectar(args.banco, somente_leitura=True) as con:
            df, diagnostico = avaliar_cruzamento(con, args.estabelecimentos, config, args.fim, args.data_analise)
        args.saida.mkdir(parents=True, exist_ok=True)
        csv = df.copy()
        csv['auditoria'] = csv.auditoria.map(lambda d: json.dumps(d, ensure_ascii=False, allow_nan=False))
        temporario = args.saida/'indice_estabelecimentos_mosler.csv.partial'
        csv.to_csv(temporario, index=False, encoding='utf-8-sig', float_format='%.10g')
        temporario.replace(args.saida/'indice_estabelecimentos_mosler.csv')
        auditoria = args.saida/'auditoria_mosler.json'
        auditoria.write_text(json.dumps({'diagnostico': diagnostico, 'estabelecimentos': json.loads(df.to_json(orient='records', force_ascii=False))},
                                       ensure_ascii=False, indent=2, allow_nan=False)+'\n')
        cobertura = df.assign(calculado=df.er_mosler.notna()).groupby('codigo_ibge_municipio', dropna=False).agg(
            estabelecimentos=('empresa_id', 'size'), calculados=('calculado', 'sum'))
        cobertura['pendentes'] = cobertura.estabelecimentos-cobertura.calculados
        cobertura.to_csv(args.saida/'cobertura_mosler.csv', encoding='utf-8-sig')
        manifesto = {'versao': config['versao'], 'status': config['status'], 'config': config,
            'csv_entrada_sha256': diagnostico['csv_sha256'], 'fontes_banco': diagnostico['fontes_banco'],
            'data_analise': diagnostico['data_analise'], 'inicio': diagnostico['inicio'], 'fim': args.fim,
            'arquivos_sha256': {}}
        for arquivo in args.saida.iterdir():
            if arquivo.name in ('indice_estabelecimentos_mosler.csv', 'auditoria_mosler.json', 'cobertura_mosler.csv'):
                manifesto['arquivos_sha256'][arquivo.name] = hashlib.sha256(arquivo.read_bytes()).hexdigest()
        (args.saida/'manifesto_mosler.json').write_text(json.dumps(manifesto, ensure_ascii=False, indent=2)+'\n')
        emitir({'calculados': diagnostico['calculados'], 'pendentes': diagnostico['pendentes'], 'csv': str(args.saida/'indice_estabelecimentos_mosler.csv'),
                'alertas': diagnostico['alertas'], 'status': config['status']})
        return 0 if diagnostico['calculados'] == diagnostico['estabelecimentos'] else 2
    with conectar(args.banco) as con:
        inicializar(con)
        if args.comando == 'iniciar':
            emitir({'banco': str(args.banco.resolve()), 'status': 'esquema_criado_sem_dados'})
        elif args.comando == 'importar-ibge':
            emitir({'municipios': importar_ibge(con, args.localidades, args.indicadores, LOCALIDADES, INDICADORES)})
        elif args.comando == 'importar-populacao':
            emitir(importar_populacao(con, args.arquivo, args.url, args.ano))
        elif args.comando == 'importar-vde':
            resultado = importar_vde(con, args.arquivo, args.url, args.somente_bruto)
            args.auditoria.parent.mkdir(parents=True, exist_ok=True)
            args.auditoria.write_text(json.dumps(resultado, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            emitir({'auditoria': str(args.auditoria), 'linhas_roubo': resultado['linhas_roubo'],
                    'observacoes_municipais_importadas': resultado['observacoes_municipais_importadas'],
                    'status': resultado['status']})
            return 0
        elif args.comando == 'importar-referencia-motor':
            emitir(importar_referencia(con, args.arquivo, args.data_analise))
        elif args.comando == 'auditar':
            emitir(auditar(con, args.estabelecimentos, args.saida))
        elif args.comando == 'resolver-fontes':
            politica = json.loads(args.politica.read_text(encoding='utf-8'))
            resultado = atualizar_hierarquia(con, politica, args.fontes, args.fim, args.saida, args.atualizar)
            emitir(resultado)
            return 2 if resultado['series_sem_fonte'] else 0
        elif args.comando == 'importar-sinesp':
            mapa = json.loads(args.mapa.read_text(encoding='utf-8')) if args.mapa else None
            resultado = importar_sinesp(con, args.arquivo, args.url, mapa)
            emitir(resultado)
            # Mantém registros de rejeição, mas não apresenta importação parcial como sucesso total.
            if resultado['rejeicoes']:
                return 2
        elif args.comando == 'gerar-indice':
            config = json.loads(args.config.read_text(encoding='utf-8'))
            df, diagnostico = gerar_indice(con, config['crimes_indice'], args.fim, config['minimo_municipios'])
            args.saida.mkdir(parents=True, exist_ok=True)
            # O mesmo resultado alimenta CSV e consulta SQLite; escrita por substituição atômica.
            df['detalhes'] = df.detalhes.map(lambda d: json.dumps(d, ensure_ascii=False, sort_keys=True))
            temporario = args.saida/'indice_municipal.csv.partial'
            df.to_csv(temporario, index=False, encoding='utf-8-sig', float_format='%.10g')
            temporario.replace(args.saida/'indice_municipal.csv')
            pd_cobertura = pd.DataFrame(diagnostico['cobertura_uf'])
            pd_cobertura.to_csv(args.saida/'cobertura_uf.csv', index=False)
            (args.saida/'diagnostico.json').write_text(json.dumps(diagnostico, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
            manifesto = {'fontes': [dict(r) for r in con.execute('SELECT url,sha256,coletado_em,metadados FROM fontes ORDER BY id')],
                         'config': config, 'arquivos_sha256': {}}
            for nome in ('indice_municipal.csv', 'cobertura_uf.csv', 'diagnostico.json'):
                with (args.saida/nome).open('rb') as f:
                    manifesto['arquivos_sha256'][nome] = hashlib.file_digest(f, 'sha256').hexdigest()
            (args.saida/'manifesto.json').write_text(json.dumps(manifesto, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            emitir({'csv': str(args.saida/'indice_municipal.csv'), 'municipios_com_indice': int(df.indice_roubo_0_100.notna().sum()), 'alertas': diagnostico['alertas']})
            return 0 if df.indice_roubo_0_100.notna().any() else 2
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError, sqlite3.Error) as exc:
        print(f'Erro: {exc}', file=sys.stderr)
        sys.exit(2)
