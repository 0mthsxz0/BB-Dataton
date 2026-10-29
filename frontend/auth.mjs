// Autenticação local de demonstração; trocar por SSO do banco antes de produção.
import { createHash, randomBytes, timingSafeEqual } from 'node:crypto';
import { readFile } from 'node:fs/promises';

const sessions = new Map();
const TTL = 4 * 3600_000;
const digest = text => createHash('sha256').update(String(text)).digest();
const equal = (a,b) => a.length === b.length && timingSafeEqual(a,b);
function cnpjValid(value) {
  const d = String(value || '').replace(/\D/g,'');
  if(d.length !== 14 || /^(\d)\1+$/.test(d)) return false;
  const check = size => {
    const weights = size===12?[5,4,3,2,9,8,7,6,5,4,3,2]:[6,5,4,3,2,9,8,7,6,5,4,3,2];
    const sum=weights.reduce((n,w,i)=>n+Number(d[i])*w,0);
    return (sum%11<2?0:11-sum%11)===Number(d[size]);
  };
  return check(12)&&check(13);
}
function cookie(id) {
  return 'bb_demo_session='+id+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=14400';
}
export function getSession(req) {
  const id=(req.headers.cookie||'').match(/(?:^|;\s*)bb_demo_session=([0-9a-f]{64})(?:;|$)/)?.[1];
  const s=id && sessions.get(id);
  if (!s) return null;
  if (s.expires < Date.now()) {sessions.delete(id);return null;}
  return s;
}
function issueSession(res,session) {
  const id=randomBytes(32).toString('hex');
  sessions.set(id,{...session,expires:Date.now()+TTL});
  res.setHeader('Set-Cookie',cookie(id));
}
export function internalLogin(res,body) {
  const password=process.env.BB_INTERNAL_PASSWORD;
  if(!password || password.length<12) return {status:503,error:'Configure BB_INTERNAL_PASSWORD com pelo menos 12 caracteres no servidor.'};
  if(!equal(digest(body.password||''),digest(password))) return {status:403,error:'Credenciais inválidas.'};
  issueSession(res,{role:'internal'});
  return {ok:true,role:'internal'};
}
export async function clientLogin(res,body) {
  const file=process.env.BB_CLIENT_MAP_FILE;
  if(!file) return {status:503,error:'A identificação bancária não está configurada neste ambiente.'};
  const cnpj=String(body.cnpj||'').replace(/\D/g,''),pin=String(body.code||'');
  if(!cnpjValid(cnpj)||pin.length<8||pin.length>128) return {status:422,error:'Confira o CNPJ e o código de verificação.'};
  let map;
  try {map=JSON.parse(await readFile(file,'utf8'));} catch {return {status:503,error:'Cadastro de vínculos indisponível.'};}
  // O mapeamento não faz parte dos CSVs anonimizados: é fornecido por um serviço de identidade externo.
  const entry=Array.isArray(map)?map.find(x=>String(x.cnpj).replace(/\D/g,'')===cnpj):null;
  const match=entry && /^[0-9a-f]{64}$/i.test(entry.codeSha256||'') && equal(digest(pin),Buffer.from(entry.codeSha256,'hex'));
  if(!match || typeof entry.empresaId!=='string'||typeof entry.imovelId!=='string')
    return {status:403,error:'Não foi possível verificar o vínculo desta empresa.'};
  issueSession(res,{role:'client',empresaId:entry.empresaId,imovelId:entry.imovelId});
  return {ok:true,role:'client',cadastroVinculado:true};
}
export function authorized(req,role) {
  const s=getSession(req);
  return s && (s.role==='internal'||(role==='client'&&s.role==='client')) ? s : null;
}
export function logout(res,req) {
  const id=(req.headers.cookie||'').match(/(?:^|;\s*)bb_demo_session=([0-9a-f]{64})(?:;|$)/)?.[1];
  if(id) sessions.delete(id);
  res.setHeader('Set-Cookie','bb_demo_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0');
}
