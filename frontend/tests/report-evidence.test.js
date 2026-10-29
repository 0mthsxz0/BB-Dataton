import test from 'node:test';
import assert from 'node:assert/strict';
import { dimensionEvidence, indexEvidence, evidenceRows, evidenceValue, assetEvidence } from '../public/report-evidence.js';

test('origin cell exposes actual numbers, CSV fields and derivation rather than only a conclusion',()=>{
  const html=dimensionEvidence({justificativa:'Cenário de teste',evidencias:[{rotulo:'Bens atribuídos',valor:50000,unidade:'BRL',origem:'Cadastro BB/Datathon',arquivo:'bens_cadastrados.csv',campo:'bens_ponderados',campos_origem:['valor_cadastrado','probabilidade_bem_no_imovel_referencia'],transformacao_origem:'Soma de valor × vínculo',estado:'CADASTRO_ESTIMATIVA',chave:{imovel_id:'IMO_TESTE'}}],dados_calculo:{bens_ponderados:50000,estoque_medio:10000},confianca:.8});
  for(const text of ['50.000,00','10.000,00','bens_cadastrados.csv','valor_cadastrado','probabilidade_bem_no_imovel_referencia','Soma de valor × vínculo','IMO_TESTE'])assert.ok(html.includes(text));
});

test('source cells show exact content, meaning and actionable confirmation without treating overrides as source data',()=>{
  const e={rotulo:'Bens atribuídos à unidade',valor:50000,unidade:'BRL',estado:'DECLARADO',origem:'Formulário',campo:'bens_ponderados',
    significado:'Soma ponderada dos bens.',fonte_utilizada:false,
    fontes_originais:[{arquivo:'bens_cadastrados.csv',linha_tabela:12,registro:'BEM_1',celulas:[
      {campo:'valor_cadastrado',valor_original:'100000.00',unidade:'BRL',significado:'Valor antes da ponderação.'},
      {campo:'probabilidade_bem_no_imovel_referencia',valor_original:'0.5000',unidade:'proporcao',significado:'Peso de vínculo, não chance de sinistro.'},
      {campo:'tipo_bem',valor_original:'<script>',unidade:'texto',significado:'Categoria do bem.'}]}],
    confirmacao:{motivo:'Ainda não foi verificado no local.',pendencias:['Presença na unidade e valor atual.'],onde_encontrar:'Inventário e notas fiscais.'}};
  for(const html of [dimensionEvidence({evidencias:[e],confianca:.8}),evidenceRows([e])]){
    for(const text of ['Linha 12','100000.00','0.5000','50%','Valor antes da ponderação.','não foram usadas','A confirmar — por quê?','Ainda não foi verificado','O que falta confirmar','Onde encontrar:','Inventário e notas fiscais.'])assert.ok(html.includes(text),text);
    assert.ok(!html.includes('<script>'));
    assert.ok(html.includes('&lt;script&gt;'));
  }
});

test('percentage conversion respects units, scale and missing values',()=>{
  assert.equal(evidenceValue(.5,'proporcao'),'50%');
  assert.equal(evidenceValue('0.50',null,'probabilidade_delivery_referencia'),'50%');
  assert.equal(evidenceValue('20',null,'percentual_receita_delivery_est'),'20%');
  assert.equal(evidenceValue(.04,null,'taxa_furto_domicilios'),'4%');
  assert.equal(evidenceValue(.6,null,'exposicao_climatica_0_1'),'60%');
  assert.equal(evidenceValue(12,null,'taxa_por_mil_estabelecimentos'),'1,2%');
  assert.equal(evidenceValue(20,'percentual'),'20%');
  assert.equal(evidenceValue(20,null,'dependencia_digital_pct'),'20%');
  assert.equal(evidenceValue(2,null,'grau_risco_nr4'),'2');
  assert.equal(evidenceValue(500,null,'estabelecimentos_referencia'),'500');
  assert.ok(evidenceValue(.5,'BRL').includes('0,50'));
  assert.equal(evidenceValue(null,'proporcao'),'Não disponível');
  const html=assetEvidence({bens:[{bem_id:'1',valor_cadastrado:100,probabilidade_vinculo:.5,valor_ponderado:50,confianca_vinculo:'MEDIA'}],vinculo:{}});
  assert.ok(html.includes('50%'));
  assert.ok(html.includes('MEDIA'));
});

test('aggregate profile is described as aggregate and excluded scope does not request missing documents',()=>{
  const html=evidenceRows([{rotulo:'Bens',valor:500,unidade:'BRL',campo:'bens_ponderados',estado:'PERFIL_ATIVIDADE_ESTIMATIVA',
    significado:'Referência estimada.',perfil_referencia:{cnae:'1234567',amostra:{empresas:12,estabelecimentos:15},metodo:'Mediana',origem:'Base fictícia'}}]);
  for(const text of ['500,00','12 empresas / 15 estabelecimentos','não corresponde a uma célula','Mediana'])assert.ok(html.includes(text),text);
  const excluded=evidenceRows([{rotulo:'Prédio',valor:0,estado:'EXCLUIDO_ESCOPO',confirmacao:{motivo:'Item fora do escopo.',pendencias:[],onde_encontrar:'Revise o escopo.'}}]);
  assert.ok(excluded.includes('Fora do escopo'));
  assert.ok(!excluded.includes('O que falta confirmar'));
});

test('index report shows raw external values and period, safely escaping source content',()=>{
  const s={nome:'Teste',prioridade:30,classe:'Baixa',prioridade_min:10,prioridade_max:50,confianca:.4,valor_exposto_brl:null,risco_evento_relativo:.3,impacto_normalizado:.5,vulnerabilidade:.5,
    explicacao_contextual:'Contexto',leitura_contextual:'Dados desta unidade',formula:'Fórmula',decomposicao:{base_pontos:30,interacao_pontos:0,efeito_limite_pontos:0},fatores_evento:[],fator_impacto:{},fator_vulnerabilidade:{},
    referencia_publica:{fonte:'https://sidra.ibge.gov.br/tabela/8510',periodo:'2021',granularidade:'MUNICIPIO',modo_acesso:'Snapshot local; sem consulta ao vivo',condicao:'Referência presente',dados:{taxa_furto_domicilios:.04,descricao_nr4:'<script>alert(1)</script>'},vinculo:{municipio:'Cidade de teste'}},respostas_utilizadas:{securityControls:null}};
  const html=indexEvidence('TESTE',s);
  for(const text of ['Dados desta unidade','2021','Conteúdo original: <code>0.04</code>','4%','Cidade de teste','sidra.ibge.gov.br','Não disponível','Parcela de domicílios','Impacto (I) = 50%','Vulnerabilidade (V) = 50%'])assert.ok(html.includes(text),text);
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(!indexEvidence('TESTE',{...s,referencia_publica:null}).includes('href="https://sidra'));
  const blocked=indexEvidence('TESTE',{...s,qualidade_seguranca:{status:'INCOMPATIVEL',data_analise:'2026-10-28',politica:'seguranca-1.0',motivos:['Vitimização domiciliar excluída <teste>']}});
  for(const text of ['Base territorial: Dados incompatíveis','Vitimização domiciliar excluída &lt;teste&gt;','2026-10-28','não é precisão estatística'])assert.ok(blocked.includes(text));
});
