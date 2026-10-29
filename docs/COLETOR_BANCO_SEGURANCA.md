# Coletor e banco público de segurança

O coletor da branch `dados-de-seguranca`, commit
`eca97ce72f9e81a80cdac99327905e791502741f`, foi integrado sobre a main nesta
branch. O contrato antes localizado em `seguranca.py` foi movido, sem alteração
de regras, para `seguranca/politica_motor.py`. Imports existentes como
`from seguranca import avaliar_seguranca` continuam funcionando.

## Código, dados e arquivos de distribuição

O Git contém o pacote `seguranca/`, as configurações em `config/`, os scripts
de preparação/validação/publicação/instalação e testes. A interface atual e o
motor da main são preservados. Os modelos CRITIC e Mosler do coletor ficam
disponíveis por comandos explícitos; não são ativados na recomendação.

Os dados ficam em `data/seguranca/`, ignorado pelo Git:

- `fontes/sinesp/bancovde-2025.xlsx`: planilha original do MJ/SINESP;
- arquivos `*.fonte.json`: URL, hash SHA-256, tamanho e instante de coleta;
- `fontes/ibge/`: respostas oficiais de localidades, área e população;
- `seguranca.sqlite`: banco de preparação, com dados e proveniência;
- `pacotes/`: diagnósticos e eventuais referências exportadas;
- `releases/<hash>/seguranca.sqlite` e manifesto adjacente: cópia consolidada
  verificada que o motor pode abrir em somente leitura.

Um clone não inclui esses arquivos. Para transportar dados entre ambientes,
transfira o pacote SQLite e seu manifesto juntos ou repita a coleta oficial.
Preserve a planilha e seus metadados separadamente se precisar reproduzir a
importação. Não adicione dados de clientes nem os CSVs privados a esse banco.

## Preparar a partir das fontes oficiais

Python 3.12/3.13, Node >=20 e as dependências existentes são suficientes.
Na raiz do checkout Linux, com a `.venv` instalada:

```bash
.venv/bin/python -m seguranca --help
.venv/bin/python scripts/preparar_banco_seguranca.py \
  --saida data/seguranca/pacotes/coleta-NOVA-EXECUCAO
```

Escolha uma pasta de saída nova a cada execução. O preparador baixa o XLSX do
SINESP VDE 2025 diretamente de `www.gov.br` e consulta o IBGE em
`servicodados.ibge.gov.br`. Reutiliza somente cache com URL e hash conferidos;
TLS permanece habilitado. A descoberta ampliada do portal está disponível em
`python -m seguranca baixar`; ela tem limites de navegação e não garante baixar
todos os documentos do portal.

O comando de preparação retorna **2** enquanto não houver referência empresarial
elegível. Consulte `preparacao.json` e `diagnostico_motor.json` na saída: uma
coleta bruta bem-sucedida pode continuar sem indicador utilizável. Com
`--sem-rede`, somente arquivos de cache já verificados são reutilizados.

O snapshot histórico tinha 69.510 registros brutos no recorte de roubo; esse
número não é uma contagem da execução atual nem uma exigência para arquivos
que a fonte venha a revisar. O arquivo original daquele snapshot tinha SHA-256
`6b87609815afc534f44f3423bf8660a69c961130c187f759b9d3e38ee2a8a6e8`.

Para inspecionar as contagens reais após a coleta:

```bash
.venv/bin/python -m seguranca resumo
```

## Publicar e conectar o SQLite ao motor

Depois de conferir a coleta, publique uma cópia consolidada. O pacote pode ser
estruturalmente válido e ainda não conter cobertura municipal elegível; não
confunda integridade com completude dos dados.

```bash
.venv/bin/python scripts/publicar_base_seguranca.py \
  --origem data/seguranca/seguranca.sqlite \
  --saida output/seguranca-release-NOVA --versao VERSAO-REVISADA
.venv/bin/python scripts/instalar_base_seguranca.py \
  --pacote output/seguranca-release-NOVA --destino data/seguranca/releases
```

O instalador retorna o caminho de `banco`. Use esse caminho, sem presumir um
hash, ao iniciar o servidor:

```bash
export BB_SEGURANCA_DB="/caminho/retornado/seguranca.sqlite"
export BB_SEGURANCA_MODO="complementar"
npm --prefix frontend start
```

Reinicie processos já abertos para aplicar a configuração. O motor consulta
SQLite diretamente por código IBGE, sem uma API externa de banco. O endpoint
local `POST /api/seguranca/municipio` apenas expõe a consulta do Python.

O modo padrão `complementar` apresenta contexto. `referencia_validada` pode
influenciar o componente de roubo apenas com referência empresarial elegível:
roubo em comércio municipal, doze meses, denominador de estabelecimentos do
mesmo ano, fontes e integridade verificadas. Vítimas, roubo de veículos/carga e
contagens estaduais não substituem essa referência. Veja
[o contrato de integração](INTEGRACAO_SEGURANCA.md).

## Rede e validação

São necessários `www.gov.br` e `servicodados.ibge.gov.br` na política de rede.
A seleção opcional de fontes estaduais em `resolver-fontes` também usa
`www.ispdados.rj.gov.br` e `ssp.rs.gov.br`; habilite esses destinos somente ao
usar esse fluxo. Não contorne bloqueios do proxy ou desabilite TLS.

Na tentativa desta integração, o proxy bloqueou os downloads oficiais. A
preparação gera o diagnóstico e um esquema vazio; isso não representa a base
de 69.510 registros nem deve ser instalado como se fosse a coleta concluída.
Após liberar a rede, execute novamente com outra pasta de saída.

```bash
.venv/bin/python -m pytest -q
npm --prefix frontend run check
npm --prefix frontend test
```

As fixtures de testes são artificiais e temporárias; não são inseridas no banco
operacional. Os testes do produtor foram adicionados sem substituir os testes
existentes do motor consumidor.
