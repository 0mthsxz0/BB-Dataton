import test from 'node:test';
import assert from 'node:assert/strict';
import {customerReport,customerRecommendationView} from '../public/journeys.js';
const r={planoId:'892',recomendacao:{plano_recomendado:'ESSENCIAL',comparacao:[{id:'892',coberturas:['a']}],necessidades:{a:{nome:'Incêndio <teste>'}},perguntas_confirmacao:[]},avisos:[],rastreabilidade:{secret:'internal'}};
test('relatório público conserva coberturas e remove dados internos',()=>{assert.deepEqual(customerReport(r).coberturas,['Incêndio <teste>']);assert.ok(!JSON.stringify(customerReport(r)).includes('secret'));assert.match(customerRecommendationView(r),/&lt;teste&gt;/);});
test('triagem bloqueada exige avaliação',()=>assert.match(customerRecommendationView({...r,recomendacao:{...r.recomendacao,indicacao_bloqueada:true}}),/precisam de avaliação/));
test('relatório acompanha pacote recalculado',()=>assert.equal(customerReport({...r,personalizacao:{pacote:{plano:'TOTAL',coberturas:[]}}}).plano,'Empresarial Total'));

test('resumo do cliente separa adicionais solicitados de sugestões sem expor evidências',()=>{
 const p={...r,personalizacao:{adicionais:[{name:'Eletrônicos',solicitada:true,candidata:true,evidencias:[{valor:'SEGREDO'}]},{name:'Delivery',candidata:true,pergunta:'Confirme entregas'}]}};
 const report=customerReport(p);
 assert.deepEqual(report.adicionais,['Eletrônicos']);assert.equal(report.sugestoes[0].nome,'Delivery');assert.ok(!JSON.stringify(report).includes('SEGREDO'));
});
