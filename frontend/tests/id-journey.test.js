import test from 'node:test';
import assert from 'node:assert/strict';
import { startIdRefinement, recommendationEndpoint } from '../public/id-journey.js';
import { riskPayload } from '../public/quote-engine.js';
import { confidenceView } from '../public/confidence-ui.js';

const catalog={activities:[{id:'909',subactivities:[{id:'mercado'}]}]};
const response={empresaId:'EMP_1',imovelId:'IMO_1',relatorio:{
  cadastro:{grupo_atividade:'MERCADO'},localizacao:{municipio_real:'Cidade',uf_real:'SP'},
  atividade:{cnaeUtilizado:'4711302'},preenchimento:{contentsValue:50000,employees:8},
  confirmacoesDisponiveis:{hasGlass:'no',glassExposed:'no'},complemento:{securityControls:false}}};

test('refinamento aproveita o cadastro e mantém perguntas sem evidência em aberto',()=>{
  const state={contentsValue:'',employees:'',hasGlass:'',glassExposed:'',securityControls:'',roofMaintained:''};
  startIdRefinement(state,response,catalog);
  assert.equal(state.contentsValue,'50000');assert.equal(state.employees,'8');
  assert.equal(state.hasGlass,'no');assert.equal(state.securityControls,'no');
  assert.equal(state.roofMaintained,'');assert.equal(state.city,'Cidade');
  assert.equal(state.activityId,'909');assert.equal(state.subactivityId,'mercado');
  assert.ok(state.prefilledFields.includes('employees'));
  const payload=riskPayload(state,{groups:[{questions:[{id:'hasGlass'},{id:'roofMaintained'}]}]});
  assert.equal(payload.empresaId,'EMP_1');assert.equal(payload.imovelId,'IMO_1');
  assert.deepEqual(payload.answers,{hasGlass:false,roofMaintained:null});
  assert.equal(recommendationEndpoint(state),'/api/demo/recomendacao');
  assert.equal(recommendationEndpoint({}),'/api/recomendacao');
});

test('cliente vê Refinar a resposta e o painel interno mantém seu editor',()=>{
  const report={recomendacao:{confianca_geral:.5}};
  report.confiancaDados={empresaId:'EMP_1',imovelId:'IMO_1',campos:[],motivos:[],limitacoes:[]};
  const customer=confidenceView(report,{refine:true});
  assert.match(customer,/Refinar a resposta/);assert.doesNotMatch(customer,/>Adicionar dados</);
  assert.match(confidenceView(report),/>Adicionar dados</);
});
