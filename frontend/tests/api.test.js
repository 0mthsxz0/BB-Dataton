import test, { after, before } from 'node:test';
import assert from 'node:assert/strict';
import { server } from '../server.mjs';
import { riskPayload } from '../public/quote-engine.js';
import { readFile } from 'node:fs/promises';

let base;
before(async()=>{await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));base=`http://127.0.0.1:${server.address().port}`;});
after(async()=>{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));});
const post=(path,payload,headers={})=>fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json',...headers},body:JSON.stringify(payload)});

test('search API returns real linked activity and subactivity',async()=>{
  const response=await post('/api/atividades/buscar',{description:'Tenho uma pizzaria e preparo pizzas para entrega'});
  assert.equal(response.status,200);
  const data=await response.json();
  assert.equal(data.catalogCount,970);
  assert.equal(data.results[0].activity.id,'625');
  assert.equal(data.results[0].subactivity.id,'R3.10');
});
test('unknown descriptions ask for clarification',async()=>{
  const data=await (await post('/api/atividades/buscar',{description:'Faço algo interessante'})).json();
  assert.equal(data.results.length,0);assert.ok(data.question);
});
test('cross-origin write requests are blocked',async()=>{
  assert.equal((await post('/api/recomendacao',{}, {Origin:'https://example.org'})).status,403);
});
test('invalid quotation fails server-side instead of returning a canned plan',async()=>{
  const response=await post('/api/recomendacao',{activityId:'inventado'});
  assert.equal(response.status,422);
  assert.match((await response.json()).error,/atividade/);
});
test('personal, address and payment fields never enter recommendation payload',async()=>{
  const schema=JSON.parse(await readFile(new URL('../public/questionnaire.json',import.meta.url),'utf8'));
  const state={name:'Privado',phone:'123',email:'test@example.com',cep:'12345678',street:'Rua Teste',payment:'card',sourceKey:'EMP_1|IMO_1'};
  const payload=riskPayload(state,schema);
  for(const k of ['name','phone','email','cep','street','payment'])assert.ok(!(k in payload));
  assert.equal(payload.empresaId,'EMP_1');
  assert.equal(Object.values(payload.answers).length,8);
  assert.ok(Object.values(payload.answers).every(v=>v===null));
});
test('public visitor cannot read internal Datathon records',async()=>{
  const context=await fetch(base+'/api/contexto');
  assert.equal(context.status,401);
  const internal=await post('/api/recomendacao/cadastro',{empresaId:'EMP_1',imovelId:'IMO_1'});
  assert.equal(internal.status,401);
  const publicLinked=await post('/api/recomendacao',{empresaId:'EMP_1',imovelId:'IMO_1'});
  assert.equal(publicLinked.status,403);
  const byCnae=await post('/api/interno/relatorio-cnae',{cnae:'4771701'});
  assert.equal(byCnae.status,401);
  const voice=await post('/api/interno/roteiros',{empresaId:'EMP_1',imovelId:'IMO_1'});
  assert.equal(voice.status,401);
});

test('passive client identification never reveals company information without verification',async()=>{
  const response=await post('/api/cliente/cadastro',{empresaId:'EMP_1',imovelId:'IMO_1'});
  assert.equal(response.status,401);
  const unconfigured=await post('/api/cliente/vincular',{cnpj:'00000000000000',code:'abcdefgh'});
  assert.ok([422,503].includes(unconfigured.status));
  const login=await fetch(base+'/interno');
  assert.equal(login.status,200);
  assert.match(await login.text(),/Acesso ao painel interno/);
});


test('demonstração pública por ID fica bloqueada até habilitação explícita',async()=>{
  const prior=process.env.BB_DEMO_ID_LOOKUP;
  try{
    delete process.env.BB_DEMO_ID_LOOKUP;
    const response=await post('/api/demo/empresa',{empresaId:'EMP_TESTE'});
    assert.equal(response.status,403);
    assert.match((await response.json()).error,/desativada/i);
    assert.equal((await post('/api/demo/recomendacao',{empresaId:'EMP_TESTE',imovelId:'IMO_TESTE'})).status,403);
  }finally{
    if(prior===undefined)delete process.env.BB_DEMO_ID_LOOKUP;
    else process.env.BB_DEMO_ID_LOOKUP=prior;
  }
});
test('interface pública mantém caminho de ID e não exibe campo CNAE para o cliente',async()=>{
  const src=await readFile(new URL('../public/quote.js',import.meta.url),'utf8');
  assert.match(src,/api\/demo\/empresa/);
  assert.match(src,/CNPJ \(produção\) \/ ID da empresa \(MVP\)/);
  assert.match(src,/customerRecommendationView\(demoResult\.relatorio,\{preliminary:true\}\)/);
  const direct=src.split('function demoReportView(){')[1].split('async function demoLookup')[0];
  assert.doesNotMatch(direct,/cadastroRecommendationView|recommendationView\(/);
  assert.match(direct,/Refinar a resposta/);
  assert.match(direct,/customerOptionalSuggestions/);
  const business=src.split('function business(){')[1].split('function address(){')[0];
  assert.match(business,/baseFields\(baseContext,state\)/);
  assert.doesNotMatch(business,/cnae-lookup|load-cnae-profile|cnae-profile-status/);
  assert.doesNotMatch(business,/Código da atividade econômica da empresa/);
});
test('consulta pública de segurança valida município e preserva bloqueio de origem',async()=>{
 assert.equal((await post('/api/seguranca/municipio',{codigoIBGE:3550308})).status,422);
 assert.equal((await post('/api/seguranca/municipio',{codigoIBGE:'3550308',uf:'SP'},{Origin:'https://example.org'})).status,403);
 const response=await post('/api/seguranca/municipio',{codigoIBGE:'3550308',uf:'SP'});
 assert.equal(response.status,200);
 const data=await response.json();assert.equal(data.contrato,'contexto-seguranca-1.0');
 assert.ok(!('empresa_id' in data));assert.ok(!('arquivo' in data));
});

test('car sales API distinguishes dealerships from independent agencies',async()=>{
  const initial=await (await post('/api/atividades/buscar',{description:'Vendo carros'})).json();
  assert.deepEqual(new Set(initial.results.map(x=>x.activity.id)),new Set(['905','906']));
  assert.equal(initial.clarification.type,'vehicleBusiness');
  for(const [value,id] of [['agency','906'],['dealer','905']]){
    const response=await post('/api/atividades/buscar',{description:'Vendo carros',refinements:{vehicleBusiness:value}});
    assert.equal(response.status,200);
    const data=await response.json();
    assert.deepEqual(data.results.map(x=>x.activity.id),[id]);
  }
});

test('search API validates and applies structured refinements',async()=>{
  const response=await post('/api/atividades/buscar',{description:'Vendo remédios',refinements:{audience:'animal'}});
  assert.equal(response.status,200);
  const data=await response.json();
  assert.equal(data.results[0].activity.id,'478');
  assert.equal(data.engine,'local-rules-tfidf-v3');
  assert.ok(data.vocabularyVersion);
  for(const refinements of [{audience:'unknown'},{operation:'__proto__'},[],null]){
    assert.equal((await post('/api/atividades/buscar',{description:'Vendo remédios',refinements})).status,422);
  }
});
