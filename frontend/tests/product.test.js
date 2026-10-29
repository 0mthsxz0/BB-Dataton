import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {initializeProductState, productPayload, syncPackageState, packageCount} from '../public/product-ui.js';

const rules=JSON.parse(await readFile(new URL('../public/product-rules.json',import.meta.url),'utf8'));

test('unknown operations stay null and personal information never enters product payload',()=>{
  const state={name:'Privado',street:'Endereço privado',email:'privado@example.com',planId:'893'};
  initializeProductState(state,rules);
  const p=productPayload(state,rules,true);
  assert.ok(Object.values(p.operations).every(x=>x===null));
  for(const key of ['name','street','email'])assert.ok(!(key in p));
  assert.equal(p.selectedPlan,'PRATICO');assert.equal(p.termYears,1);
});

test('manual package preserves separate preference, adjustment and conditional-extra contracts',()=>{
  const state={planId:'893'};initializeProductState(state,rules);
  state.adjust_QUEBRA_DE_VIDROS='include';state.want_QUEBRA_DE_VIDROS=true;
  state.op_refrigeration='yes';state.extra_DETERIORACAO_MERCADORIAS_FRIGORIFICADAS=true;
  state.termYears='3';
  const p=productPayload(state,rules,true);
  assert.deepEqual(p.coverageAdjustments.include,['QUEBRA_DE_VIDROS']);
  assert.deepEqual(p.indispensable,['QUEBRA_DE_VIDROS']);
  assert.deepEqual(p.optionalCovers,['DETERIORACAO_MERCADORIAS_FRIGORIFICADAS']);
  assert.equal(p.operations.refrigeration,true);assert.equal(p.termYears,3);
  assert.ok(!('coverageAdjustments' in productPayload(state,rules)));
});

test('changing unit resets operational confirmations and package preferences',()=>{
  const state={};initializeProductState(state,rules);
  state.op_delivery='yes';state.extra_DELIVERY=true;state.adjust_QUEBRA_DE_VIDROS='exclude';state.priority='terceiros';
  initializeProductState(state,rules);
  assert.equal(state.op_delivery,'');assert.equal(state.extra_DELIVERY,false);
  assert.equal(state.adjust_QUEBRA_DE_VIDROS,'');assert.equal(state.priority,'equilibrada');
});

test('composição retornada inicializa todas as proteções e total unificado',()=>{
 const state={};initializeProductState(state,rules);
 const r={personalizacao:{pacote:{plano:'PRATICO',adicionais_condicionais:['DELIVERY','EQUIPAMENTOS_ELETRONICOS'],quantidade_coberturas:10}}};
 syncPackageState(r,state,rules);assert.equal(state.planId,'893');assert.equal(state.extra_DELIVERY,true);assert.equal(packageCount(r),10);
 state.excludeExtra_DELIVERY=true;assert.deepEqual(productPayload(state,rules,true).optionalExclusions,['DELIVERY']);
});
