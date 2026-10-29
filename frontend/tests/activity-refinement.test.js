import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createActivityIndex,searchActivities,positiveDescription,isValidSelection} from '../public/activity-search.js';
import {validRefinements} from '../public/activity-vocabulary.js';
const catalog=JSON.parse(await readFile(new URL('../public/activities.json',import.meta.url),'utf8'));
const index=createActivityIndex(catalog);
const search=(q,refinements={})=>searchActivities(index,q,{mode:'description',limit:3,refinements});

test('car sales returns both catalog business types and asks the actual distinction',()=>{
  for(const q of ['Vendo carros','vendo carro','Vendo automóveis','Vendo carros usados','Minha empresa vende carros']){
    const r=search(q);
    assert.deepEqual(new Set(r.results.map(x=>x.activity.id)),new Set(['905','906']),q);
    assert.equal(r.clarification?.type,'vehicleBusiness',q);
    assert.equal(r.confidence,'ambiguous');
  }
  assert.equal(search('Vendo carros',{vehicleBusiness:'agency'}).results[0].activity.id,'906');
  assert.equal(search('Vendo carros',{vehicleBusiness:'dealer'}).results[0].activity.id,'905');
});

test('vehicle use and components do not become whole-car sales',()=>{
  for(const [q,id] of [['Conserto carros','633'],['Fabrico carros','821'],['Lavo carros','683'],['Vendo peças de carros','501']])assert.equal(search(q).results[0]?.activity.id,id,q);
  const rental=search('Alugo carros');
  assert.ok(rental.results.some(x=>x.activity.id==='697'));
  assert.ok(rental.results.every(x=>['697','954'].includes(x.activity.id)));
  assert.notEqual(rental.clarification?.type,'operation');
});

test('short descriptions work across previously uncovered retail segments',()=>{
  for(const [q,id] of [['Vendo motos','908'],['Vendo bicicletas','907'],['Vendo sapatos','486'],['Vendo sandálias','486'],['Vendo brinquedos','522'],['Vendo ferramentas','493'],['Vendo cimento','497'],['Vendo geladeiras','510'],['Vendo celulares','508'],['Vendo pneus','501'],['Vendo bananas','468']])assert.equal(search(q).results[0]?.activity.id,id,q);
  assert.ok(!search('Vendo motos').results.some(x=>x.activity.id==='907'));
  assert.ok(!search('Vendo bicicletas').results.some(x=>x.activity.id==='908'));
});

test('generic selling language is insufficient product evidence',()=>{
  for(const q of ['Vendo coisas','Trabalho com vendas','Tenho uma loja','Vendo produtos diversos','Comércio em geral'])assert.equal(search(q).results.length,0,q);
  assert.equal(search('Não vendo carros, vendo sapatos').results[0]?.activity.id,'486');
});

test('short meaningful descriptions and popular medicine aliases work',()=>{
  for(const q of ['Vendo remédios','remedio','remédios','Tenho uma farmácia','farmácia','Tenho uma drograria'])assert.equal(search(q).results[0]?.activity.id,'476',q);
});
test('medicine operations and audiences select different catalog activities',()=>{
  for(const [q,id] of [['Vendo remédios para animais','478'],['Vendo medicamentos veterinários no atacado','555'],['Vendo medicamentos no atacado','553'],['Fabrico medicamentos','291'],['Fabrico medicamentos veterinários','292']])assert.equal(search(q).results[0]?.activity.id,id,q);
});
test('negative clauses preserve the following positive statement',()=>{
  for(const separator of [', ','. ',' mas ','; ',' e sim ']){
    const q='Não vendo medicamentos'+separator+'vendo cosméticos';
    assert.equal(search(q).results[0]?.activity.id,'477',q);
    assert.ok(!search(q).results.some(r=>r.activity.id==='476'));
  }
  assert.equal(positiveDescription('Nunca fabrico roupas, vendo roupas'),'vendo roupas');
  assert.equal(search('Não vendo medicamentos').results.length,0);
});
test('structured answers refine audience and mixed operations without losing context',()=>{
  const initial=search('Vendo remédios');assert.equal(initial.clarification.type,'audience');assert.equal(initial.confidence,'ambiguous');
  const refined=search('Vendo remédios',{audience:'animal'});assert.equal(refined.results[0].activity.id,'478');assert.notEqual(refined.clarification?.type,'audience');
  assert.equal(search('Vendo e fabrico roupas').clarification.type,'operation');
  assert.equal(search('Vendo e fabrico roupas',{operation:'retail'}).results[0].activity.id,'484');
  assert.equal(search('Vendo e fabrico roupas',{operation:'manufacture'}).results[0].activity.id,'855');
});
test('consulting specialty and premises have separate refinements',()=>{
  assert.equal(search('Faço consultoria para empresas').clarification.type,'specialty');
  const r=search('Faço consultoria para empresas',{specialty:'finance',premises:'ground'});
  assert.equal(r.results[0].activity.id,'674');assert.equal(r.results[0].subactivity?.id,'E6.40');
});
test('only allowed refinement keys and answers are accepted',()=>{
  for(const value of [null,[],{operation:'invented'},{unknown:'retail'},{operation:{}}])assert.equal(Boolean(validRefinements(value)),false);
  assert.equal(validRefinements({audience:'animal',operation:'wholesale'}),true);
});
test('all returned identifiers and relationships remain catalog-owned',()=>{
  for(const q of ['Vendo remédios','Faço consultoria','Vendo e fabrico roupas','conserto celualr','pizaria','Não vendo medicamentos, vendo cosméticos']){
    for(const r of search(q).results){assert.ok(catalog.activities.some(a=>a.id===r.activity.id));if(r.subactivity)assert.ok(isValidSelection(catalog,r.activity.id,r.subactivity.id));}
  }
});
