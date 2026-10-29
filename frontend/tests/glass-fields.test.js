import test from 'node:test';
import assert from 'node:assert/strict';
import {riskFields,riskPayload} from '../public/quote-engine.js';
const questionnaire={notice:'',groups:[]};
const field=(key,label,options={})=>`<input name="${key}" aria-label="${label}"><small>${options.help||''}</small>`;
test('cliente informa quantidade; consultor conserva valor de reposição',()=>{
 const customer=riskFields({},questionnaire,field);
 assert.match(customer,/name="glassCount"/);assert.doesNotMatch(customer,/name="glassValue"/);assert.match(customer,/janelas, portas de vidro, vitrines e espelhos/);
 const consultant=riskFields({},questionnaire,field,{internal:true});assert.match(consultant,/name="glassValue"/);
});
test('quantidade chega ao motor em campo próprio',()=>{
 const p=riskPayload({glassCount:'8'},questionnaire);assert.equal(p.glassCount,'8');assert.equal(p.glassValue,undefined);
});
