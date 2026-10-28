/** Read-only smoke check of the running local app. No proposals are saved. */
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
const base = process.env.BB_FRONTEND_URL || 'http://localhost:4174';
const evidence = {checkedAt:new Date().toISOString(),checks:[]};
async function request(route,payload) {
  const res=await fetch(base+route,payload===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  assert.equal(res.status,200,`${route}: ${res.status} ${res.ok?'':await res.text()}`);
  return res.json();
}
const schema=JSON.parse(await readFile(new URL('../frontend/public/questionnaire.json',import.meta.url),'utf8'));
const search=await request('/api/atividades/buscar',{description:'Tenho uma pizzaria e preparo pizzas para entrega'});
assert.equal(search.results[0].activity.id,'625');assert.equal(search.results[0].subactivity.id,'R3.10');
evidence.checks.push({check:'Busca com IDs reais e subatividade vinculada',status:'PASS',activity:'625',subactivity:'R3.10'});
const context=await request('/api/contexto');
const establishment=context.estabelecimentos.find(r=>r.label.includes('FARMACIA'));
if(establishment){
  const initial=await request('/api/recomendacao/cadastro',{empresaId:establishment.empresaId,imovelId:establishment.imovelId});
  assert.equal(initial.preliminar,true);assert.equal(initial.respostas,null);assert.equal(initial.atividade.id,null);
  assert.equal(Object.keys(initial.indices).length,4);
  assert.equal(initial.recomendacao.comparacao.length,3);
  for(const p of initial.recomendacao.comparacao){
    const sum=Object.entries(initial.recomendacao.necessidades).reduce((total,[code,n])=>total+(p.coberturas.includes(code)?n.prioridade*n.peso:0),0);
    assert.ok(Math.abs(sum-p.pontos_atendidos)<1e-8);
  }
  const traceSum=initial.rastreabilidade.bens.reduce((sum,b)=>sum+(b.valor_ponderado||0),0);
  assert.ok(Math.abs(traceSum-initial.patrimonio.bens_ponderados)<1e-6);
  assert.ok(initial.indices.ROUBO_FURTO_ARROMBAMENTO.referencia_publica.dados.taxa_furto_domicilios!=null);
  assert.equal(initial.indices.QUEBRA_DE_VIDROS.referencia_publica,null);
  assert.ok(initial.dimensionamento.ROUBO_FURTO_ARROMBAMENTO.evidencias.some(e=>e.arquivo==='sinais_financeiros_operacionais.csv'));
  evidence.checks.push({check:'Recomendação imediata apenas pelo cadastro, sem respostas presumidas',status:'PASS',
    suggestedPlan:initial.recomendacao.plano_recomendado,questionnaireAnswers:initial.respostas,
    plans:initial.recomendacao.comparacao.map(p=>({plan:p.plano,fit:p.aderencia_percentual}))});
}
const catalog=JSON.parse(await readFile(new URL('../frontend/public/activities.json',import.meta.url),'utf8'));
const activity=establishment?catalog.activities.find(a=>a.id==='476'):search.results[0].activity;
const payload={activityId:activity.id,subactivityId:activity.subactivities[0].id,protection:'both',shopping:'no',
  city:establishment?.city||'São Paulo',uf:establishment?.uf||'SP',
  empresaId:establishment?.empresaId||'',imovelId:establishment?.imovelId||'',
  answers:Object.fromEntries(schema.groups.flatMap(g=>g.questions.map(q=>[q.id,true])))};
const result=await request('/api/recomendacao',payload);
assert.equal(Object.keys(result.indices).length,4);
assert.equal(Object.keys(result.recomendacao.necessidades).length,10);
assert.equal(result.recomendacao.comparacao.length,3);
assert.ok(result.recomendacao.comparacao.some(p=>p.id===result.planoId&&p.apto_simulacao));
assert.equal(result.recomendacao.comparacao[2].aderencia_percentual,100);
assert.ok(!('email' in result));assert.ok(!('name' in result));
evidence.checks.push({check:'Motor Python por HTTP, quatro índices e dez necessidades',status:'PASS',
  linkedLocalBase:result.vinculoBase,establishmentsAvailable:context.estabelecimentos.length,
  sources:result.fontes.map(f=>({type:f.tipo,available:f.disponivel,period:f.periodo})),
  plans:result.recomendacao.comparacao.map(p=>({plan:p.plano,fit:p.aderencia_percentual})),
  confirmedMunicipality:Boolean(result.localizacao.codigo_ibge_municipio)});
const custom=await request('/api/recomendacao',{...payload,selectedPlan:'PRATICO',priority:'continuidade',termYears:3,
  operations:{refrigeration:true},coverageAdjustments:{include:['QUEBRA_DE_VIDROS'],exclude:[]},
  optionalCovers:['DETERIORACAO_MERCADORIAS_FRIGORIFICADAS']});
assert.equal(custom.personalizacao.pacote.plano,'PRATICO');
assert.equal(custom.personalizacao.pacote.vigencia_anos,3);
assert.equal(custom.personalizacao.pacote.coberturas.length,9);
assert.ok(custom.personalizacao.pacote.obrigatorias.every(c=>custom.personalizacao.pacote.coberturas.includes(c)));
assert.deepEqual(custom.personalizacao.pacote.adicionais_condicionais,['DETERIORACAO_MERCADORIAS_FRIGORIFICADAS']);
const blocked=await request('/api/recomendacao',{...payload,propertyStatus:'EM_OBRA'});
assert.equal(blocked.recomendacao.indicacao_bloqueada,true);
const invalid=await fetch(base+'/api/recomendacao',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({...payload,coverageAdjustments:{exclude:['PROTECAO_CIBERNETICA_AVALIAR']}})});
assert.equal(invalid.status,422);
evidence.checks.push({check:'Personalização, adicionais condicionais, vigência, triagem e obrigatórias validados no servidor',status:'PASS',
  defaultFit:result.personalizacao.pacote.aderencia_percentual,customFit:custom.personalizacao.pacote.aderencia_percentual,
  customCovers:custom.personalizacao.pacote.coberturas.length,termYears:3,mandatoryExclusionStatus:invalid.status});
const output=new URL('../frontend/docs/evidence/integracao-mvp-http.json',import.meta.url);
await writeFile(output,JSON.stringify(evidence,null,2)+'\n');
console.log(JSON.stringify(evidence,null,2));
