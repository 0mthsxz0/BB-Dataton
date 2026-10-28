import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createActivityIndex, searchActivities, isValidSelection } from '../public/activity-search.js';

const catalog=JSON.parse(await readFile(new URL('../public/activities.json',import.meta.url),'utf8'));
const source=JSON.parse(await readFile(new URL('../catalog-source/activities.json',import.meta.url),'utf8')).dados.lsAlternativa;
const relations=JSON.parse(await readFile(new URL('../catalog-source/subactivities-by-activity.json',import.meta.url),'utf8'));
const index=createActivityIndex(catalog);

test('all 970 source activities and all 1007 relationships are preserved',()=>{
  assert.equal(catalog.activities.length,970);
  assert.deepEqual(catalog.activities.map(a=>a.id).sort(),source.map(a=>a.nrCodigo).sort());
  assert.equal(new Set(catalog.activities.map(a=>a.id)).size,970);
  assert.equal(catalog.activities.reduce((n,a)=>n+a.subactivities.length,0),1007);
  for(const a of catalog.activities){
    assert.deepEqual(a.subactivities.map(s=>s.id).sort(),relations[a.id].map(s=>String(s.nrCodigo)).sort());
    assert.equal(a.sourceLabel,source.find(x=>x.nrCodigo===a.id).nmDescritivo);
  }
});
test('display labels remove the main source abbreviations for every option',()=>{
  const pattern=/(?<!\p{L})(FABR|ATACAD|VAREJ|MAQ|APAR|EQUIP|ARTEF|CLASSIF|PROD|PREP|COMPUT|INSTR|TRANSP|ENERG|CONSTR|FRIGORIF|ADMINIST|ASSOCIAC|BRINQUED|CICLOMOT|COMUN|CONCENTR|CONFEDER|FISCALIZ|METALURG|PUBLICIT|TREFILAD)(?!\p{L})/iu;
  for(const row of catalog.activities){assert.ok(!pattern.test(row.label),row.label);assert.ok(row.label.length>0);for(const sub of row.subactivities)assert.ok(!pattern.test(sub.label),sub.label);}
});
const cases=[
  ['pizza and delivery','Tenho uma pizzaria e preparo pizzas para entrega','625','R3.10'],
  ['beauty services','Corto cabelo e faço barba e manicure','641','C1.10'],
  ['clothing retail','Vendo roupas em uma loja para consumidores','484',null],
  ['wood furniture production','Fabrico moveis de madeira sob medida','226',null],
  ['computer repair','Faço manutenção e conserto de computadores e notebooks','1007','E1.40'],
  ['custom software','Desenvolvemos software sob encomenda para clientes','1008',null],
  ['grocery','Tenho um mercadinho com produtos de limpeza e alimentos','909',null],
  ['dentist','Trabalho com odontologia e atendo pacientes','690',null],
  ['accounting','Sou contador e presto serviços de contabilidade para empresas','674',null],
  ['laundry','Tenho uma lavanderia e lavamos roupas de clientes','640',null],
  ['negative manufacturing context','Não fabrico roupas, vendo roupas em uma loja','484',null],
];
for(const [name,query,id,subId] of cases)test(`description: ${name}`,()=>{
  const result=searchActivities(index,query,{mode:'description',limit:3});
  assert.equal(result.results[0]?.activity.id,id,JSON.stringify(result.results.map(r=>({id:r.activity.id,score:r.score}))));
  if(subId)assert.equal(result.results[0].subactivity?.id,subId);
  for(const r of result.results){assert.ok(catalog.activities.some(a=>a.id===r.activity.id));if(r.subactivity)assert.ok(isValidSelection(catalog,r.activity.id,r.subactivity.id));}
});
test('empty description asks for detail instead of selecting any activity',()=>{
  for(const query of ['', 'empresa','Faço algo interessante','zzqjkzx sem coisa definida']){
    const result=searchActivities(index,query,{mode:'description'});assert.equal(result.results.length,0,query);assert.ok(result.question,query);
  }
});
test('name search supports accents, approximate spelling and internal identifiers',()=>{
  assert.equal(searchActivities(index,'pizaria').results[0].activity.id,'625');
  assert.equal(searchActivities(index,'625').results[0].activity.id,'625');
  assert.ok(searchActivities(index,'comercio varejista de vestuario',{limit:20}).results.some(r=>r.activity.id==='484'));
});
test('browse mode exposes the complete list rather than an arbitrary first page',()=>{
  assert.equal(searchActivities(index,'',{limit:catalog.activities.length}).results.length,970);
});
test('subactivity cannot be carried across an incompatible parent',()=>{
  assert.equal(isValidSelection(catalog,'625','R3.10'),true);
  assert.equal(isValidSelection(catalog,'641','R3.10'),false);
  assert.equal(isValidSelection(catalog,'unknown','R3.10'),false);
});
test('unsupported parents have no invented automatic subactivity',()=>{
  const empty=catalog.activities.filter(a=>!a.subactivities.length);assert.equal(empty.length,10);
  for(const a of empty){const r=searchActivities(index,a.id,{limit:1}).results[0];assert.equal(r.activity.id,a.id);assert.equal(r.subactivity,null);}
});
