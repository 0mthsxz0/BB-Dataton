import test from 'node:test';
import assert from 'node:assert/strict';
import { newDraft, approve, makeCall, status } from '../voice-service.mjs';
import { clientLogin, getSession, internalLogin } from '../auth.mjs';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import path from 'node:path';

const report={
 cadastro:{descricao_cnae:'Comércio de alimentos'},
 localizacao:{municipio_real:'Brasília'},
 indices:{ROUBO_FURTO_ARROMBAMENTO:{nome:'Roubo e furto',prioridade:80}},
 recomendacao:{plano_recomendado:'PRATICO',comparacao:[{plano:'PRATICO',coberturas:['ROUBO_FURTO_ARROMBAMENTO']}],perguntas_confirmacao:[]},
 avisos:['Documentos ainda não confirmados']
};
test('roteiro é construído apenas da recomendação e precisa de aprovação humana',async()=>{
 const d=await newDraft(report,{empresa:'Loja Teste',organizacao:'Equipe Teste'});
 assert.match(d.text,/voz automatizada/i);
 assert.match(d.text,/Prático/);
 assert.match(d.text,/Loja Teste/);
 assert.equal(status(d.id).approved,false);
 await assert.rejects(makeCall({id:d.id,phone:'+5561999999999',confirmed:true,authorizedContact:true},'/tmp'),/Revise e aprove/);
 await assert.rejects(async()=>approve({id:d.id,text:'Preço garantido R$ 99 hoje e seguro aprovado!'}),/Roteiro|promessa/i);
 const a=approve({id:d.id,text:d.text});
 assert.equal(status(d.id).approved,true);
 await assert.rejects(makeCall({id:d.id,approvalHash:a.approvalHash,phone:'+5561999999999',authorizedContact:false,confirmed:true},'/tmp'),/autorizar|confirmar/i);
 await assert.rejects(makeCall({id:d.id,approvalHash:a.approvalHash,phone:'+5561999999999',authorizedContact:true,confirmed:true},'/tmp'),/desativadas|Twilio/);
 assert.equal(status(d.id).used,false);
});
test('login interno não admite senha padrão sem configuração',()=>{
 const prior=process.env.BB_INTERNAL_PASSWORD;
 delete process.env.BB_INTERNAL_PASSWORD;
 const res={setHeader(){}};
 assert.equal(internalLogin(res,{password:'qualquer'}).status,503);
 if(prior!==undefined)process.env.BB_INTERNAL_PASSWORD=prior;
});
test('vínculo externo é verificado e limitado a uma empresa',async()=>{
 const dir=await mkdtemp(path.join(tmpdir(),'bb-test-'));
 const file=path.join(dir,'map.json');
 const old=process.env.BB_CLIENT_MAP_FILE;
 try{
  const code='codigo-somente-teste123';
  await writeFile(file,JSON.stringify([{cnpj:'11444777000161',empresaId:'EMP_1',imovelId:'IMO_1',codeSha256:createHash('sha256').update(code).digest('hex')}]));
  process.env.BB_CLIENT_MAP_FILE=file;
  const fail={setHeader(){}};
  assert.equal((await clientLogin(fail,{cnpj:'11444777000161',code:'codigo-errado'})).status,403);
  let cookie;
  const ok={setHeader:(k,v)=>{if(k==='Set-Cookie')cookie=v;}};
  assert.equal((await clientLogin(ok,{cnpj:'11444777000161',code})).ok,true);
  const session=getSession({headers:{cookie:cookie.split(';')[0]}});
  assert.equal(session.role,'client');
  assert.equal(session.empresaId,'EMP_1');
  assert.equal(session.imovelId,'IMO_1');
 }finally{if(old===undefined)delete process.env.BB_CLIENT_MAP_FILE;else process.env.BB_CLIENT_MAP_FILE=old;await rm(dir,{recursive:true,force:true});}
});
