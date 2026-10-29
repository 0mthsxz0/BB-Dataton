"""Produz release imutável de um SQLite público. Nunca importa dados de clientes."""
import argparse
from contextlib import closing
from datetime import datetime,timezone
import hashlib,json,shutil,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contexto_seguranca import FORMATO,VERSAO_SCHEMA,validar_pacote


def publicar(origem,saida,versao):
    origem,saida=Path(origem).resolve(),Path(saida).resolve()
    if not origem.is_file():raise ValueError('Banco de origem inexistente.')
    if not isinstance(versao,str) or not 1<=len(versao)<=100:raise ValueError('Informe a versão dos dados.')
    saida.mkdir(parents=True,exist_ok=False)
    try:
        banco=saida/'seguranca.sqlite'
        with closing(sqlite3.connect(origem.as_uri()+'?mode=ro',uri=True)) as src, closing(sqlite3.connect(banco)) as dest:
            src.backup(dest)
        with banco.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        m={'formato':FORMATO,'versao_schema':VERSAO_SCHEMA,'versao_dados':versao,'arquivo':banco.name,
           'sha256':digest,'gerado_em':datetime.now(timezone.utc).isoformat()}
        Path(str(banco)+'.manifesto.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        validar_pacote(banco)
        return m
    except BaseException:
        shutil.rmtree(saida)
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--origem',type=Path,required=True);p.add_argument('--saida',type=Path,required=True);p.add_argument('--versao',required=True)
    a=p.parse_args()
    try:print(json.dumps(publicar(a.origem,a.saida,a.versao),ensure_ascii=False,indent=2))
    except (ValueError,OSError,sqlite3.Error) as e:p.exit(2,str(e)+'\n')
