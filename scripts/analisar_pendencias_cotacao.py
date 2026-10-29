"""Estatísticas agregadas por estabelecimento; desconhecido não é inelegível."""
from pathlib import Path
import sys,csv,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from processamento import carregar_base,numero,NULOS
from produto import triagem
base=carregar_base();records=base.estabelecimentos.to_dict('records');n=len(records)
out=Path(__file__).resolve().parents[1]/'entregas'/'diagnostico-cotacao';out.mkdir(parents=True,exist_ok=True)
def count(fn):return sum(bool(fn(r)) for r in records)
def missing(r,c):return r.get(c) is None or str(r.get(c)).strip().upper() in NULOS
def row(motivo,q,parametro,nota):return dict(motivo=motivo,unidades=q,percentual=round(100*q/n,2),denominador=n,parametro=parametro,observacao=nota)
restricoes=[
row('Atividade rural: sinal pelo CNAE',count(lambda r:str(r.get('cnae_principal','')).replace('-','').replace('/','')[:2] in ('01','02','03')),'Divisões CNAE 01, 02 ou 03','Nenhum sinal rural nos CNAEs fornecidos; confirmar atividade efetiva e aceitação.'),
row('Localização rural ou nas áreas restritas do guia',0,'Confirmação específica da localização','Não verificável em 100%: sem campo próprio. Não inferir de renda, bairro, CEP ou coordenadas perturbadas. Zero identificado não prova ausência.'),
row('Imóvel tombado ou desapropriado',0,'Confirmação documental específica','Não verificável em 100%: sem campos próprios.'),
row('Imóvel condenado',count(lambda r:r.get('situacao_imovel_cadastral')=='CONDENADO'),'situacao_imovel_cadastral = CONDENADO','Nenhum registro com esse valor. IRREGULAR não equivale a condenado.'),
row('Construção, reforma ou reconstrução',count(lambda r:r.get('situacao_imovel_cadastral') in ('EM_OBRA','EM_CONSTRUCAO','EM_REFORMA','EM_RECONSTRUCAO')),'Situação em obra/construção/reforma/reconstrução','EM_OBRA é o único impedimento explícito encontrado. Confirmar situação atual antes de decisão oficial.'),
row('Paredes externas combustíveis',count(lambda r:r.get('material_parede_externa_cadastrado') in ('MADEIRA','MATERIAL_COMBUSTIVEL')),'Material = MADEIRA ou MATERIAL_COMBUSTIVEL','Nenhum positivo informado; em 2.524 unidades o material é desconhecido.'),
row('Mesmo objeto em outra proposta BB Seguros',0,'Checar objeto, proposta/apólice existente','Não verificável em 100%: sem histórico de propostas por objeto.'),
row('Objeto básico acima de R$ 7,5 milhões',count(lambda r:(numero(r.get('bens_ponderados')) or 0)+(numero(r.get('estoque_medio_estimado')) or 0)>7500000),'Prédio e conteúdo, limite único > 7.500.000','Encaminhar ao Personalizado; não é recusa geral. Nenhum subtotal disponível supera o corte, mas falta reconstrução em 100%. Não comprova valor total abaixo do limite.')]
pendencias=[
row('Identificação legal: nome/razão social e CPF/CNPJ',n,'Identificação legal válida; IDs anônimos não substituem CPF/CNPJ','Ausência estrutural do pacote anonimizado, não falha do cliente real.'),
row('Relação com o imóvel',n,'Confirmar proprietário ou inquilino','Pagamento de aluguel ou sua ausência não comprova a relação jurídica.'),
row('Escopo: prédio, conteúdo ou ambos',n,'Escolha explícita do cliente','Define quais valores são aplicáveis. Não consta nos CSVs.'),
row('Condições do local e aceitação da atividade',n,'Confirmar restrições e atividade aceita no produto','CNAE preenchido não comprova aceitação; o pacote não confirma toda a lista do guia.'),
row('CEP completo e validado',count(lambda r:len(str(r.get('cep_agregado','')))!=8 or not str(r.get('cep_agregado','')).isdigit()),'CEP completo de oito dígitos','cep_agregado não é CEP completo. Logradouro, número, bairro, cidade e UF estão preenchidos.'),
row('Empregados confirmados nesta unidade',n,'Quantidade local confirmada ou ausência declarada','Há estimativa empresarial e folha local; sem confirmação por unidade.'),
row('Reconstrução ou dispensa explícita pelo escopo',n,'Reconstrução sem terreno para prédio/ambos; dispensável se conteúdo apenas','Pendência de aplicabilidade: o escopo ainda é desconhecido em todos os registros.'),
row('Bens, equipamentos e estoque confirmados',n,'Inventário atual, vínculo e valor de reposição na unidade','Há estimativas agregadas, sem validação atual para cotação.'),
row('Plano e adicionais com aceitação da atividade',n,'Sugestão do motor e validação de compatibilidade/aceitação','Plano pode ser calculado; não equivale a cotação concluída ou aceitação.'),
row('Refrigeração confirmada',n,'Sim/Não; se Sim, mercadorias e valores','Probabilidade estimada não substitui resposta.'),
row('Delivery confirmado',n,'Sim/Não; se Sim, detalhar operação','Receita/probabilidade estimadas não substituem resposta.'),
row('Home office confirmado',n,'Sim/Não; se Sim, bens e locais de uso','Vendas online não comprovam trabalho remoto.'),
row('Dinheiro/valores em caixa confirmados',n,'Sim/Não; se Sim, quantia e controles','Recebimentos não digitais não equivalem a dinheiro em caixa.'),
row('Eletrônicos: exposição e inventário confirmados',n,'Confirmar uso e reposição na unidade','Bens cadastrados são sinais, não confirmação atual.'),
row('Segurança física e controles digitais confirmados',n,'Confirmar controles efetivos; verificar requisitos de shopping quando aplicáveis','Bem SISTEMA_SEGURANCA e maturidade digital não comprovam controles. Condições para desconto não são exclusões gerais.'),
row('Material das paredes ausente',count(lambda r:missing(r,'material_parede_externa_cadastrado')),'Ausente ou NAO_DISPONIVEL','Impede verificação de combustível; não classificar ausência como material combustível.'),
row('Padrão construtivo ausente',count(lambda r:missing(r,'padrao_construtivo_cadastrado')),'Ausente ou NAO_DISPONIVEL','Parâmetro de apoio ao dimensionamento, não exclusão autônoma do guia.'),
row('Ao menos um bem com vínculo de baixa confiança',count(lambda r:(numero(r.get('bens_baixa_confianca')) or 0)>0),'bens_baixa_confianca > 0','Prioridade de revisão de inventário; não taxa de inelegibilidade.'),
row('Endereço incompatível com cadastro',count(lambda r:r.get('endereco_cnpj_compativel')!='SIM'),'endereco_cnpj_compativel != SIM','Conferir vínculo/endereço; divergência não é proibição automática.'),
row('Situação cadastral irregular',count(lambda r:r.get('situacao_imovel_cadastral')=='IRREGULAR'),'situação = IRREGULAR','Apurar; não equiparar automaticamente a condenado ou em obra.')]
disponibilidade=[]
for nome,campo in [('CNAE','cnae_principal'),('Atividade descrita','descricao_cnae'),('Faturamento empresarial','faturamento_mensal'),('Empregados estimados da empresa','quantidade_funcionarios_estimada'),('Folha local','folha_pagamento_mensal'),('Bens agregados','bens_ponderados'),('Equipamentos agregados','equipamentos_ponderados'),('Estoque estimado','estoque_medio_estimado'),('Despesas fixas estimadas','despesa_fixa_mensal_estimada'),('Aluguel identificado','valor_aluguel_recorrente')]:
 disponibilidade.append(row(nome,count(lambda r:missing(r,campo)),campo,'Ausência literal. Presença não comprova confirmação contratual. Zero válido é preservado.'))
bloqueados=count(lambda r:triagem(r)['bloqueado'])
summary={'base':'Desenvolvimento','data':'2026-10-28','estabelecimentos':n,'empresas':len({r['empresa_id'] for r in records}),'impedimento_explicito':bloqueados,'impedimento_pct':round(100*bloqueados/n,2),'sem_impedimento_explicito_mas_pendentes':n-bloqueados,'pendentes_pct':round(100*(n-bloqueados)/n,2),'prontos_demonstraveis_apenas_com_csv':0,'unidades_de_empresas_com_filiais':count(lambda r:(numero(r.get('quantidade_unidades')) or 0)>1),'hashes':{str(k).replace('\\\\','/').rsplit('/',1)[-1]: v for k,v in base.hashes.items()}}
for name,items in [('inelegibilidade',restricoes),('pendencias',pendencias),('disponibilidade',disponibilidade)]:
 with (out/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
(out/'diagnostico.json').write_text(json.dumps(dict(resumo=summary,restricoes=restricoes,pendencias=pendencias,disponibilidade=disponibilidade),ensure_ascii=False,indent=2),encoding='utf-8')
def pct(q):return f'{100*q/n:.2f}'.replace('.',',')+'%'
def table(items):
 return '| Motivo / parâmetro | Unidades | % da base | Regra e interpretação |\n|---|---:|---:|---|\n'+''.join(f"| {x['motivo']} | {x['unidades']} | {pct(x['unidades'])} | {x['parametro']}. {x['observacao']} |\n" for x in items)
report=f'''# Diagnóstico de elegibilidade e informações mínimas de cotação

Base: **{n} estabelecimentos de {summary['empresas']} empresas**, desenvolvimento. Data: 28/10/2026.
Fonte normativa do desafio: Guia_Times_Datathon_Protecao_Inteligente_Final.pdf, seção 10.1, p. 13; seção 10.2, pp. 14–15 para planos. Dados: empresas, endereços, sinais financeiros, bens, território e dicionário dos CSVs locais. Não inclui respostas de sessões do navegador nem verificação oficial da seguradora.

## Resultado sem dupla contagem

- **{bloqueados} unidades ({pct(bloqueados)})** com impedimento explícito cadastrado: em obra.
- **{n-bloqueados} unidades ({pct(n-bloqueados)})** sem impedimento explícito identificado, com verificações mínimas pendentes.
- **Zero unidades demonstradamente prontas para cotação completa apenas pelos CSVs**: o pacote anonimizado não contém identificação legal e confirmações contratuais/operacionais. Isso não é uma taxa de rejeição real.
- Entre os impedimentos identificados, **obra representa 100% dos casos**. Os critérios sem informação não entram nessa composição: zero identificado não significa zero existente.

## Metodologia dos percentuais

Percentual = unidades com o motivo / {n} × 100. No resultado geral o impedimento tem precedência; nas tabelas por motivo uma unidade pode aparecer em várias linhas, por isso os percentuais não devem ser somados. O denominador de cada linha é a base inteira, inclusive imóveis em obra. Ausência, estimativa sem confirmação e dado incompatível são apresentados separadamente de impedimento.

## Todos os critérios de inelegibilidade e encaminhamento

'''+table(restricoes)+'''
## Lacunas de informação e confirmação; motivos de revisão

'''+table(pendencias)+'''
## Dados disponíveis: percentual de ausência literal

'''+table(disponibilidade)+f'''
## Parâmetros propostos para o sistema

1. **IMPEDIMENTO_IDENTIFICADO**: condição proibida explicitamente registrada. Atualmente são os {bloqueados} registros EM_OBRA. Não inferir material combustível ou localização restrita por proxies.
2. **ENCAMINHAMENTO_PERSONALIZADO**: prédio/conteúdo acima de R$ 7,5 milhões. Soma parcial inferior não confirma enquadramento sem escopo e reconstrução aplicável.
3. **PENDENTE_CONFIRMACAO**: falta de informação aplicável, estimativas não confirmadas, divergência cadastral ou irregularidade a esclarecer. Não é rejeição automática.
4. **SEM_LACUNAS_MINIMAS_DEMONSTRADAS**: informações mínimas aplicáveis verificadas, ainda sujeito a aceitação oficial. Nenhum registro pode ser demonstrado nessa condição apenas com o pacote atual.
5. Campos condicionais: **SIM / NAO / DESCONHECIDO / NAO_APLICAVEL**, com justificativa para dispensa. Reconstrução é exigida para prédio/ambos; requisitos do shopping condicionam desconto, não aceitação universal.
6. Não misturar motivos de impedimento e informação faltante em uma nota com pesos arbitrários. Usar contagem de estabelecimentos por motivo para priorizar a coleta.

## Prioridade de coleta

Primeiro, identificação legal, relação com o imóvel, escopo, CEP completo e declarações de elegibilidade. Depois, revisar paredes (84,75% ausentes), padrão construtivo (81,83%), vínculo de bens (61,35% com ao menos um bem de baixa confiança) e endereço (22,03% divergentes). Os 52 registros IRREGULAR exigem esclarecimento; não foram contabilizados como inelegíveis. Há {summary['unidades_de_empresas_com_filiais']} unidades pertencentes a empresas com múltiplos estabelecimentos: não distribuir faturamento ou empregados igualmente sem evidência. Isso é contexto de qualidade, não falta de dado autônoma.

Ausências estruturais do pacote anônimo não representam falhas do cliente. Valores de bens, despesas, estoque e aluguel podem estar preenchidos e ainda exigir confirmação de reposição/aplicabilidade. Sem preços, franquias e aceitação, não se trata de proposta concluída.

Reproduzir: `.venv/Scripts/python.exe scripts/analisar_pendencias_cotacao.py`. Saídas agregadas, sem identificação individual. O JSON registra os hashes das entradas para auditoria.
'''
(out/'relatorio.md').write_text(report,encoding='utf-8')
assert bloqueados==sum(r['situacao_imovel_cadastral']=='EM_OBRA' for r in records)
assert bloqueados+(n-bloqueados)==n
print(json.dumps(summary|{'hashes':'registrados no JSON'},ensure_ascii=False))
for r in pendencias[15:]:print(r['motivo'],r['unidades'],r['percentual'])
