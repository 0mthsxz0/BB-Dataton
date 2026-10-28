"""Build display labels from the frozen public insurer catalog. No network."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'frontend' / 'catalog-source'
OUTPUT = ROOT / 'frontend' / 'public' / 'activities.json'

# Editorial expansions preserve the insurer's internal identifiers. They do not
# convert the catalog into CNAE, nor assert insurer-approved descriptions.
EXPANSIONS = {
    'FABR':'fabricação','FABRIC':'fabricação','FAB':'fabricação','FABRICACAO':'fabricação',
    'MAQ':'máquinas','MAQUIN':'máquinas','MAQUINAS':'máquinas','APAR':'aparelhos','APAREL':'aparelhos',
    'EQUIP':'equipamentos','EQUIPAM':'equipamentos','EQUIPAMEN':'equipamentos','EQUIPAMENTOS':'equipamentos',
    'ATACAD':'atacadista','VAREJ':'varejista','SERV':'serviços','SERVICO':'serviço','SERVICOS':'serviços',
    'PROD':'produtos','PRODU':'produção','PRODUC':'produção','PRODUTOS':'produtos','ARTEF':'artefatos',
    'PECAS':'peças','PECA':'peça','ACES':'acessórios','ACESS':'acessórios','ACESSOR':'acessórios','ACESSORIOS':'acessórios',
    'ADM':'administração','ADMIN':'administração','ADMINISTRACAO':'administração','PUB':'pública','FED':'federal','EST':'estadual','MUN':'municipal',
    'IND':'indústria','INDUS':'indústria','INDUST':'indústria','INDUSTR':'indústria','INDUSTRIA':'indústria',
    'ESPEC':'especificados','ESPECF':'especificados','ESPECIF':'especificados','ESPECIFIC':'especificados',
    'CLASSIF':'classificados','CLASSIFIC':'classificados','CLAS':'classificados','CL':'classificados','CLASS':'classificados','CLASSI':'classificados',
    'MAT':'materiais','MATER':'materiais','MATERIA':'matéria','AUX':'auxiliares','CONSERV':'conservação','DERIV':'derivados','DER':'derivados',
    'CONSTR':'construção','CONST':'construção','CONSTRUCAO':'construção','DOMEST':'doméstico','DOM':'doméstico',
    'PLAST':'plástico','PLASTIC':'plástico','PLASTICO':'plástico','TECN':'técnica','MAD':'madeira','ODONTO':'odontológico',
    'ESCRIT':'escritório','ESCR':'escritório','ESCRITORIO':'escritório','FERR':'ferramentas','MET':'metais',
    'PROFIS':'profissionais','PROF':'profissionais','PROFISSION':'profissionais','EXPLOR':'exploração',
    'INST':'instalação','INSTAL':'instalação','INSTALACAO':'instalação','INSTALACOES':'instalações',
    'LOC':'locação','LOCAC':'locação','LOCACAO':'locação','VEIC':'veículos','VEICULOS':'veículos',
    'UTENS':'utensílios','UTENSILIOS':'utensílios','CARB':'carbono','CART':'cartão','CARTOL':'cartolina',
    'OUT':'outros','OUTR':'outros','AROMAT':'aromáticas','ASSEM':'assemelhados','TECID':'tecidos',
    'MEDIC':'médico','MEDICO':'médico','HOSPIT':'hospitalares','HOSP':'hospitalares','HOSPITAR':'hospitalares',
    'AGROPEC':'agropecuária','AGROP':'agropecuária','COMBUST':'combustíveis','PREC':'precisão','PREST':'prestação',
    'MANUT':'manutenção','MANUTEN':'manutenção','MANUTENCAO':'manutenção','REPARA':'reparação','REPAR':'reparação','REPARACAO':'reparação',
    'TRANSP':'transporte','ENERG':'energia','ENER':'energia','ENERGIA':'energia','ELETR':'elétricos','ELE':'elétrica',
    'ELETRICA':'elétrica','ELETRICOS':'elétricos','ELETRON':'eletrônicos','ELETRONICOS':'eletrônicos','ELETROT':'eletrotécnicos',
    'ELEVA':'elevação','ELEVACAO':'elevação','COMPUT':'computadores','DESENV':'desenvolvimento','DESENVOLVIM':'desenvolvimento',
    'ENCOM':'encomenda','CONSULT':'consultoria','TELECOMUNIC':'telecomunicações','TREF':'trefilados','SEGUR':'segurança','SEG':'segurança',
    'ESQUAD':'esquadrias','PESS':'pessoal','PESSOAL':'pessoal','DEST':'destilação','BENEFIC':'beneficiamento','BENEF':'beneficiamento',
    'BEL':'bélico','BELICO':'bélico','AUTOM':'automação','CHAP':'chapas','REVEST':'revestimento','ARTIF':'artificiais',
    'CONFEC':'confecção','CONFECCAO':'confecção','CONFECCOES':'confecções','ESTRUT':'estruturas','OBJ':'objetos',
    'FERRAG':'ferragens','FERRAM':'ferramentas','MINER':'mineração','COMUNIC':'comunicação','LUBRIF':'lubrificantes',
    'INSTR':'instrumentos','MUSIC':'musicais','VEGET':'vegetais','ALIM':'alimentação','ALIMENT':'alimentícios',
    'DISTR':'distribuição','DISTRIB':'distribuição','DISTRIBUICAO':'distribuição','FINANC':'financeira','CRED':'crédito','CREDITO':'crédito',
    'PRODUCAO':'produção','EMPR':'empresas','EXPORT':'exportação','EMBAL':'embalagens','PORTAT':'portáteis',
    'RECEP':'recepção','REPROD':'reprodução','RODOV':'rodoviários','FRIGOR':'frigorificação','PEQ':'pequenos',
    'ONDUL':'ondulado','RELAM':'relaminação','RETREF':'retrefilação','PERF':'perfis','ESTAMP':'estampagem','TRANSM':'transmissão','TRASMS':'transmissão',
    'TERRRAPLENAGEM':'terraplenagem','CARREG':'carregamento','MONT':'montagem','MILIT':'militar','ELETROQ':'eletroquímicos',
    'SISTEM':'sistemas','DED':'dedicados','GERENC':'gerenciamento','PERIF':'periféricos','CRONOM':'cronômetros',
    'IMAG':'imagem','EMBARC':'embarcações','CARP':'carpintaria','PLAC':'placas','AGLOM':'aglomerada',
    'PRENS':'prensada','COMPENS':'compensada','TALHA':'talhados','MOBIL':'mobiliário','PAP':'papel','BORR':'borracha',
    'NATUR':'natural','SINTET':'sintética','ORGANO':'organometálicos','ORG':'orgânicos','BASIC':'básicos','BASICOS':'básicos',
    'INTER':'intermediários','PETROQ':'petroquímicos','MIN':'minerais','VEG':'vegetal','COSMET':'cosméticos','PREPAR':'preparações',
    'EMB':'embalagens','RECUP':'recuperação','POLIPR':'polipropileno','POLIET':'polietileno','INFANTO':'infanto',
    'GORD':'gorduras','CAPR':'caprinos','REP':'preparação','POS':'pós','LABOR':'laboratoriais','LABORAT':'laboratoriais','LABORATOR':'laboratoriais',
    'SUBST':'substâncias','CONCRET':'concreto','HIDRAUL':'hidráulicas','VETERIN':'veterinários','DECOR':'decoração',
    'CUTEL':'cutelaria','ADUB':'adubos','FERT':'fertilizantes','ELAB':'elaboração','QUIM':'químicos','GASOL':'gasolina',
    'MAG':'magnéticos','GRAV':'gravados','RECREAT':'recreativos','CRIAC':'criação','RESID':'resíduos','SORVET':'sorvetes',
    'FARMAC':'farmacêuticos','MEDICIN':'medicinais','QUIMIC':'químicos','CUT':'cutelaria','CAL':'calçados','COMERC':'comerciais',
    'CARBUR':'carburantes','MAGN':'magnéticos','GRA':'gravação','PEDR':'pedras','CERAM':'cerâmicos','VIV':'vivos',
    'RESTAUR':'restaurantes','CHURRASC':'churrascarias','LANCH':'lanchonetes','PAST':'pastelarias','CONFEIT':'confeitarias','SALG':'salgados',
    'ARTIG':'artigos','VESTUAR':'vestuário','PEDIC':'pedicure','MANIC':'manicure','INSTIT':'institutos','ESPETAC':'espetáculos',
    'CULT':'culturais','ESPORT':'esportivas','PRAT':'práticas','ARQUIT':'arquitetura','ASSES':'assessoria','ASSESORIA':'assessoria',
    'GEOD':'geodésia','PROSPEC':'prospecção','FISC':'fiscalização','OBR':'obras','LEV':'levantamentos','TOPOG':'topográficos',
    'HIGIEN':'higienização','DOMIC':'domiciliares','BCO':'banco','JURID':'jurídicos','CONTAB':'contábeis','PELIC':'películas',
    'FOT':'fotografia','SOC':'sociedades','SOCIED':'sociedades','ESTUD':'estúdios','FOTOG':'fotográficos',
    'EMPRES':'empresariais','ENTID':'entidades','PROM':'promoção','ASSIST':'assistência','ARREND':'arrendamento',
    'EMPREST':'empréstimo','TIT':'títulos','INVEST':'investimentos','VID':'vidros','CRIST':'cristais','PROCES':'processamento',
    'PADRO':'padronizados','DEP':'depósito','MERC':'mercadorias','PASSAG':'passageiros','COMPART':'compartimentos',
    'PORT':'portões','BAT':'batentes','GRAD':'grades','BASC':'basculantes','MECAN':'mecânica','MOTR':'motrizes',
    'HIDR':'hidráulicas','CENTRIF':'centrífugas','ALC':'álcool','AGUARDE':'aguardente','GRAF':'gráfica','MARM':'mármore',
    'AGRIC':'agrícolas','EXEC':'exercício','ESPT':'esportes','FISICOS':'físicos','SAUDE':'saúde','MUNICIPIO':'município',
    'NAO':'não','ACO':'aço','ACUCAR':'açúcar','ACAO':'ação','MOVEIS':'móveis','TEXTEIS':'têxteis','TEXTIL':'têxtil',
    'GAS':'gás','ALCOOL':'álcool','QUIMICO':'químico','CARVAO':'carvão','OLEOS':'óleos','AEREO':'aéreo',
    'SUINOS':'suínos','AGUA':'água','ARROZ':'arroz','CAFÉ':'café','CAFE':'café','PAPELAO':'papelão',
    'CRIACAO':'criação','EXTRACAO':'extração','PETROLEO':'petróleo','UTILIZACAO':'utilização','COMERCIO':'comércio',
    'DOMESTICO':'doméstico','DOMESTICOS':'domésticos','ENERGETICOS':'energéticos','ELETRICO':'elétrico','INFORMATICA':'informática',
    'MEDICA':'médica','CIVICAS':'cívicas','TECNICO':'técnico','TECNICA':'técnica','BOLO':'bolo','BELEZA':'beleza',
    'TERMICOS':'térmicos','TERMICO':'térmico','CERAMICA':'cerâmica','CERAMICOS':'cerâmicos','MUSICA':'música',
    'PLANTACAO':'plantação','FIACAO':'fiação','METALICO':'metálico','METALICAS':'metálicas','METALICOS':'metálicos',
    'SINTETICOS':'sintéticos','SINTETICAS':'sintéticas','ESPECIFICADOS':'especificados','EDICAO':'edição',
    'PREPARACAO':'preparação','CONSERVACAO':'conservação','FABRICAS':'fábricas','AUTOMOVEIS':'automóveis',
    'ACESSORIO':'acessório','HIGIENICOS':'higiênicos','HIDRAULICAS':'hidráulicas','PROTECAO':'proteção',
    'FARMACEUTICOS':'farmacêuticos','ALIMENTACAO':'alimentação','IMOVEIS':'imóveis','ESTACAO':'estação',
    'TELEFONICOS':'telefônicos','OTICOS':'óticos','OPTICOS':'ópticos','OPTICAS':'ópticas','OPTICA':'óptica',
    'SALAO':'salão','BOVINOS':'bovinos','FERTILIZANTES':'fertilizantes','CONSTRUCOES':'construções',
    'DEPOSITO':'depósito','DEPOSITOS':'depósitos','ESPECIFICACAO':'especificação','FRIGORIFICACAO':'frigorificação',
    'METALURGIA':'metalurgia','SERVICOS':'serviços','HOTEIS':'hotéis','MOTEIS':'motéis','ENSINO':'ensino',
    'CIENCIA':'ciência','TELECOMUNICACOES':'telecomunicações','OTICO':'ótico','ODONTOLOGICO':'odontológico',
    'ODONTOLOGICOS':'odontológicos','ESTETICA':'estética','RESTAURACAO':'restauração','DECORACAO':'decoração',
    'MUNICOES':'munições','MUNICAO':'munição','CRONOMETROS':'cronômetros','MOVEIS':'móveis','ONIBUS':'ônibus',
    'ORGAOS':'órgãos','SEGURANCA':'segurança','ADMINISTRATIVA':'administrativa','ELETRONICA':'eletrônica',
    'ARTIFICIAIS':'artificiais','CONTABEIS':'contábeis','JURIDICOS':'jurídicos','TOPOGRAFICOS':'topográficos',
    'TRR':'transportador-revendedor-retalhista','GLP':'gás liquefeito de petróleo','ETC':'entre outros',
    'ART':'artigos','PREP':'preparação','ANIM':'animais','ESTR':'estruturas','LA':'lã',
    'ESCRITORIOS':'escritórios','TERREOS':'térreos','CABELEREIROS':'cabeleireiros','INFLAMAVEIS':'inflamáveis','INFLAMAVEL':'inflamável',
    'INTERMUN':'intermunicipal','GASTRO':'gastronômicos','TELE':'telecomunicações','ESTOFO':'estofamento','SINT':'sintéticos',
    'ESTUQ':'estuque','EMBALAG':'embalagens','ELEVAÇAO':'elevação','CONVENIENCIAS':'conveniências',
    'ESTACOES':'estações','AEROVIARIAS':'aeroviárias','RODOVIARIAS':'rodoviárias','PORTUARIAS':'portuárias',
    'SALÕES':'salões','SALOES':'salões','FOTOGRAFICOS':'fotográficos','ESTUDIOS':'estúdios','LABORATORIOS':'laboratórios',
    'INTALACOES':'instalações','GINASIOS':'ginásios','ESTADIOS':'estádios','DANCA':'dança','GINASTICA':'ginástica',
    'MOVEIS':'móveis','SAUDE':'saúde','AGENCIA':'agência','AGENCIAS':'agências','ECONOMICO':'econômico','IMOBILIARIO':'imobiliário',
}

OVERRIDES = {
    '625':'Restaurantes, churrascarias, pizzarias, cantinas e pensões de alimentação',
    '641':'Cabeleireiros, barbeiros, salões de beleza, pedicure, manicure e calistas',
    '674':'Serviços de escritório, jurídicos, contábeis, auditoria e assessoria técnica financeira',
    '1007':'Manutenção, reparação e instalação de computadores, equipamentos e periféricos',
    '1006':'Desenvolvimento e edição de programas de computador para comercialização',
    '1008':'Desenvolvimento sob encomenda e outras consultorias em programas de computador',
    '1000':'Manutenção e reparação de redes, aparelhos e equipamentos de energia elétrica',
    '1002':'Manutenção e reparação de redes, aparelhos e equipamentos de telecomunicações',
    '1004':'Fabricação de máquinas, aparelhos, peças e equipamentos para transporte e elevação de cargas',
    '470':'Padarias, bombonieres e confeitarias',
    '636':'Reparação de artigos e acessórios do vestuário e de artigos de tecidos',
    '909':'Comércio varejista de mercadorias em geral — mercearias',
    '951':'Franquias de alimentação',
    'R3.10':'Restaurantes e pizzarias',
    'A2.10':'Academias de ginástica, esportes, dança, luta e condicionamento físico',
    'B3.10':'Bares, lanchonetes e pastelarias',
    '587':'Comércio atacadista de máquinas, aparelhos e equipamentos odontológicos, médico-hospitalares e laboratoriais',
    '678':'Serviços de fotografia pessoal, sociedades e estúdios fotográficos para fins comerciais e industriais',
    '179':'Fabricação de máquinas, aparelhos e equipamentos de sistemas elétricos dedicados à automação e ao gerenciamento',
    'C1.10':'Cabeleireiros, salões de beleza e estética, com vendas de artigos de perfumaria',
    'A8.10':'Agências de turismo',
    'F6.20':'Lojas de flores artificiais',
    '103':'Fabricação de ferramentas eletrotécnicas para instalação de redes e subestações de energia elétrica e de telecomunicações',
    '730':'Educação especial e atendimento a estudantes superdotados e com deficiência',
    '736':'Autoescolas — centros de formação de condutores',
    '908':'Comércio varejista de motocicletas, triciclos, ciclomotores, peças e acessórios',
    '825':'Fabricação de carrocerias, peças e acessórios para outros veículos automotores rodoviários',
}

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text) if not unicodedata.combining(c)).upper()

def expand(text, code):
    if code in OVERRIDES:
        return OVERRIDES[code]
    text = normalized(text).strip()
    text = re.sub(r'\bCOM\s+(?=VAREJ|ATACAD)', 'COMERCIO ', text)
    text = re.sub(r'\bP\s*/\s*', 'PARA ', text)
    text = re.sub(r'\bP\b', 'PARA', text)
    text = text.replace('E/OU','E OU').replace('INFRA-ESTRUTURA','INFRAESTRUTURA')
    text = re.sub(r'\bODONTO[- ]MEDIC(?:O)?[- ]HOSPIT(?:AL|AR)?\b','ODONTOLOGICOS, MEDICOS E HOSPITALARES', text)
    text = re.sub(r'\bOFF\s*SET\b','IMPRESSAO OFFSET',text)
    text = re.sub(r'\bON\s*LINE\b','EM LINHA',text)
    text = re.sub(r'[A-Z0-9]+', lambda m: EXPANSIONS.get(m[0], m[0].lower()), text)
    text = re.sub(r'\s*,\s*', ', ',text)
    text = re.sub(r'\s*/\s*', ' / ',text)
    text = re.sub(r'\s+', ' ',text).strip(' .')
    text = re.sub(r'(?<=\w)\.(?=\s|$)', '', text)
    return text[:1].upper()+text[1:]

def build():
    raw = json.loads((SOURCE / 'activities.json').read_text(encoding='utf-8'))['dados']['lsAlternativa']
    mapping = json.loads((SOURCE / 'subactivities-by-activity.json').read_text(encoding='utf-8'))
    missing = [r['nrCodigo'] for r in raw if r['nrCodigo'] not in mapping]
    if missing:
        raise ValueError(f'Missing parent mappings: {missing[:10]}')
    rows = []
    for item in raw:
        code = item['nrCodigo']
        sub = mapping[code]
        rows.append({'id':code,'label':expand(item['nmDescritivo'],code),'sourceLabel':item['nmDescritivo'],
            'subactivities':[{'id':str(s['nrCodigo']),'label':expand(s['nmDescritivo'],str(s['nrCodigo'])),'sourceLabel':s['nmDescritivo']} for s in sub]})
    rows.sort(key=lambda r: normalized(r['label']))
    result = {'capturedAt':'2026-10-28','source':'https://cotacaoseguroempresarial.bbseguros.com.br/home',
        'sourceEndpoint':'/api/simulador/ultron/general/atividade-economica',
        'labelPolicy':'Expansões editoriais para leitura; códigos internos preservados. Não equivale ao catálogo CNAE.',
        'counts':{'activities':len(rows),'subactivityRelations':sum(len(r['subactivities']) for r in rows)},'activities':rows}
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result['counts']))

if __name__ == '__main__':
    build()
