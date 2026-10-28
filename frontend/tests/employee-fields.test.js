import test from 'node:test';
import assert from 'node:assert/strict';
import {riskFields,riskPayload,employeePresence,syncEmployeeExposure} from '../public/quote-engine.js';
const questionnaire={notice:'',groups:[{name:'Empregador',code:'RESPONSABILIDADE_CIVIL_EMPREGADOR',questions:[{id:'hasEmployees',text:'Há empregados trabalhando neste estabelecimento?'},{id:'hazardousWork',text:'Há exposição física nas tarefas?'}]}]};
const field=(key,label)=>`<input name="${key}" aria-label="${label}">`;
test('quantidade é perguntada uma única vez antes dos valores sem repetir Sim/Não',()=>{
 const html=riskFields({},questionnaire,field);
 assert.equal((html.match(/name="employees"/g)||[]).length,1);
 assert.doesNotMatch(html,/Há empregados trabalhando/);assert.doesNotMatch(html,/name="hasEmployees"/);
 assert.ok(html.indexOf('risk-questions')<html.indexOf('Valores do estabelecimento'));
 assert.ok(html.indexOf('name="employees"')<html.indexOf('Valores do estabelecimento'));
});
test('zero, positivo e vazio preservam significados distintos no payload',()=>{
 for(const [employees,expected] of [['0',false],['5',true],['',null]]){
  const r=riskPayload({employees,hazardousWork:'no'},questionnaire);assert.equal(r.answers.hasEmployees,expected);
 }
 assert.equal(employeePresence({employees:'1.5'}),null);
});
test('zero dispensa exposição; ao voltar a ter empregados é preciso responder novamente',()=>{
 const s={employees:'0',hazardousWork:'yes'};syncEmployeeExposure(s,'3');assert.equal(s.hazardousWork,'no');
 s.employees='2';syncEmployeeExposure(s,'0');assert.equal(s.hazardousWork,'');
});
