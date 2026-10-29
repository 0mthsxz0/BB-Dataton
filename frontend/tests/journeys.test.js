import test from 'node:test';
import assert from 'node:assert/strict';
import {customerReport,customerRecommendationView,customerOptionalSuggestions} from '../public/journeys.js';
const r={planoId:'892',recomendacao:{plano_recomendado:'ESSENCIAL',comparacao:[{id:'892',coberturas:['a']}],necessidades:{a:{nome:'Incêndio <teste>'}},perguntas_confirmacao:[]},avisos:[],rastreabilidade:{secret:'internal'}};
test('relatório público conserva coberturas e remove dados internos',()=>{assert.deepEqual(customerReport(r).coberturas,['Incêndio <teste>']);assert.ok(!JSON.stringify(customerReport(r)).includes('secret'));assert.match(customerRecommendationView(r),/&lt;teste&gt;/);});
test('triagem bloqueada exige avaliação',()=>assert.match(customerRecommendationView({...r,recomendacao:{...r.recomendacao,indicacao_bloqueada:true}}),/precisam de avaliação/));
test('relatório acompanha pacote recalculado',()=>assert.equal(customerReport({...r,personalizacao:{pacote:{plano:'TOTAL',coberturas:[]}}}).plano,'Empresarial Total'));

test('resultado do cliente exibe a confiança do cálculo atual, inclusive após enriquecimento',()=>{
 for(const [confianca,texto] of [[.33,'33%'],[.678,'67,8%'],[0,'0%']]){
  const result={...r,recomendacao:{...r.recomendacao,confianca_geral:confianca}};
  assert.equal(customerReport(result).confiancaGeral,confianca);
  assert.ok(customerRecommendationView(result).includes(`Confiança dos dados: <strong>${texto}</strong>`));
 }
 assert.match(customerRecommendationView(r),/Confiança dos dados: <strong>Não disponível<\/strong>/);
});

test('resumo reúne proteções em lista única sem expor sugestões ou evidências',()=>{
 const p={...r,personalizacao:{adicionais:[{name:'Eletrônicos',solicitada:true,candidata:true,evidencias:[{valor:'SEGREDO'}]},{name:'Delivery',candidata:true,pergunta:'Confirme entregas'}]}};
 const report=customerReport(p);
 assert.ok(report.coberturas.includes('Eletrônicos'));assert.ok(!report.coberturas.includes('Delivery'));assert.ok(!('adicionais' in report));assert.ok(!('sugestoes' in report));assert.ok(!JSON.stringify(report).includes('SEGREDO'));
});

test('resposta rápida do cliente distingue sugestões das coberturas incluídas e omite evidências internas',()=>{
 const result={...r,personalizacao:{adicionais:[
  {name:'Delivery <teste>',candidata:true,confirmacao:null,evidencias:[{valor:'DADO_INTERNO'}]},
  {name:'Eletrônicos',candidata:true,solicitada:true},
  {name:'Numerário',candidata:true,confirmacao:false},
  {name:'Lucro bruto simples',candidata:true,operation:'interruption'},
  {name:'Lucro líquido ampla',candidata:true,operation:'interruption'}
 ]}};
 const html=customerRecommendationView(result,{preliminary:true})+customerOptionalSuggestions(result);
 assert.match(html,/Sua proteção inicial/);assert.match(html,/Delivery &lt;teste&gt;/);
 assert.match(html,/ainda não estão incluídas/);assert.doesNotMatch(html,/Numerário|DADO_INTERNO|Memória de cálculo|questionario|CSV/);
 assert.equal(customerReport(result).coberturas.includes('Delivery <teste>'),false);
 assert.equal(html.split('Proteção do lucro em caso de interrupção').length-1,1);
 assert.doesNotMatch(html,/Lucro bruto simples|Lucro líquido ampla/);
});
