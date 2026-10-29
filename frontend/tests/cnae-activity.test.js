import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createActivityIndex } from '../public/activity-search.js';
import { classificarCnae } from '../public/cnae-activity.js';
const catalog=JSON.parse(await readFile(new URL('../public/activities.json',import.meta.url),'utf8'));
const index=createActivityIndex(catalog);

test('CNAE 4771-7/01 identifica farmácias e a subatividade existente do catálogo',()=>{
 const r=classificarCnae({cnae:'4771701',encontrado:true,descricao:'Comércio varejista de produtos farmacêuticos sem manipulação'},catalog,index);
 assert.equal(r.tipo,'automatico');
 assert.equal(r.activityId,'476');
 assert.equal(r.subactivityId,'F2.20');
 assert.match(r.descricao,/farmacêuticos/);
});
test('sem correspondência verificada não atribui empresa nem inventa atividade',()=>{
 const r=classificarCnae({cnae:'9999999',encontrado:false,descricao:''},catalog,index);
 assert.equal(r.tipo,'nao_encontrado');
 assert.equal(r.activityId,undefined);
});
test('CNAE não substitui validação do catálogo de seguradora',()=>{
 const modified={...catalog,activities:catalog.activities.filter(x=>x.id!=='476')};
 const modifiedIndex=createActivityIndex(modified);
 const r=classificarCnae({cnae:'4771701',encontrado:true,descricao:'Comércio varejista de produtos farmacêuticos sem manipulação'},modified,modifiedIndex);
 assert.notEqual(r.tipo,'automatico');
});
test('cotação pública não deve exibir quantidade de empresas ou aplicar medianas pelo CNAE',async()=>{
 const quote=await readFile(new URL('../public/quote.js',import.meta.url),'utf8');
 assert.match(quote,/api\/cnae\/atividade/);
 assert.match(quote,/if\(choice\.tipo==='automatico'\)/);
 assert.match(quote,/completed=Math\.max\(completed,2\)/);
 assert.match(quote,/go\(2\)/);
 assert.match(quote,/if\(!internal\)/);
 assert.match(quote,/fields=\(internal\?'':/);
 assert.doesNotMatch(quote,/p\.amostra\.empresas/);
});
