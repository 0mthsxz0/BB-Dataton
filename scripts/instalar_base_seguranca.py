"""Instala pacote local verificado em diretório próprio por hash; sem trocar código."""
import argparse,json,os,shutil,sqlite3,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contexto_seguranca import validar_pacote


def instalar(pacote,destino):
    pacote,destino=Path(pacote).resolve(),Path(destino).resolve()
    m=validar_pacote(pacote/'seguranca.sqlite')
    destino.mkdir(parents=True,exist_ok=True)
    final=destino/m['sha256']
    if final.exists():
        existente=validar_pacote(final/'seguranca.sqlite')
        if existente!=m:raise ValueError('Release existente com metadados diferentes; não sobrescrever.')
    else:
        temporario=Path(tempfile.mkdtemp(prefix='.seguranca-',dir=destino))
        try:
            for nome in ['seguranca.sqlite','seguranca.sqlite.manifesto.json']:
                shutil.copyfile(pacote/nome,temporario/nome)
            validar_pacote(temporario/'seguranca.sqlite')
            os.rename(temporario,final)
        finally:
            if temporario.exists():shutil.rmtree(temporario)
    return {'banco':str(final/'seguranca.sqlite'),'versao_dados':m['versao_dados'],'sha256':m['sha256'],
            'modo_recomendado':'complementar','configuracao':'Defina BB_SEGURANCA_DB com o caminho banco e reinicie a aplicação.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pacote',type=Path,required=True);p.add_argument('--destino',type=Path,default=Path('data/seguranca/releases'))
    a=p.parse_args()
    try:print(json.dumps(instalar(a.pacote,a.destino),ensure_ascii=False,indent=2))
    except (ValueError,OSError,sqlite3.Error) as e:p.exit(2,str(e)+'\n')
