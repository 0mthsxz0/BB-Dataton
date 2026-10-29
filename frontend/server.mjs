import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { createActivityIndex, searchActivities } from './public/activity-search.js';
import { internalLogin, clientLogin, authorized, getSession, logout } from './auth.mjs';
import { newDraft, approve, makeCall, status as draftStatus } from './voice-service.mjs';

const root = path.resolve(fileURLToPath(new URL('./public/', import.meta.url)));
const project = path.resolve(root, '../..');
const port = Number(process.env.PORT || 4174);
const venv = path.join(project, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.BB_PYTHON || (existsSync(venv) ? venv : process.platform === 'win32' ? 'python' : 'python3');
const catalog = JSON.parse(await readFile(path.join(root, 'activities.json'), 'utf8'));
const index = createActivityIndex(catalog);
let running = 0;

function json(res, status, data) {
  res.writeHead(status, { 'Content-Type':'application/json; charset=utf-8', 'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff' });
  res.end(JSON.stringify(data));
}

export function runMotor(request) {
  if (running >= 4) return Promise.reject(Object.assign(new Error('Motor ocupado. Tente novamente em alguns segundos.'), {status:503}));
  running++;
  return new Promise((resolve, reject) => {
    const child = spawn(python, ['-X', 'utf8', path.join(project, 'scripts', 'api_cotacao.py')], { cwd:project, windowsHide:true, stdio:['pipe','pipe','ignore'] });
    let output = '', settled = false;
    const finish = (error, value) => {
      if (settled) return;
      settled = true; running--; clearTimeout(timer);
      error ? reject(error) : resolve(value);
    };
    const timer = setTimeout(() => { child.kill(); finish(Object.assign(new Error('O motor excedeu o tempo de consulta. Tente novamente.'),{status:504})); }, 30000);
    child.on('error', () => finish(new Error('Python indisponível. Configure BB_PYTHON ou instale as dependências.')));
    child.stdin.on('error', () => {});
    child.stdout.on('data', chunk => {
      output += chunk.toString('utf8');
      if (output.length > 8e6) { child.kill(); finish(new Error('Resposta do motor excedeu o limite.')); }
    });
    child.on('close', code => {
      if (code !== 0) { finish(new Error('Falha ao executar o motor Python. Confira as dependências.')); return; }
      try {
        const result = JSON.parse(output);
        result.ok ? finish(null, result.data) : finish(Object.assign(new Error(result.error), {status:result.status}));
      } catch { finish(new Error('Resposta inválida do motor.')); }
    });
    child.stdin.end(JSON.stringify(request));
  });
}

async function body(req) {
  if (!/^application\/json(?:;|$)/i.test(req.headers['content-type'] || '')) throw Object.assign(new Error('Envie JSON.'),{status:415});
  let text = '';
  req.setEncoding('utf8');
  for await (const chunk of req) {
    text += chunk;
    if (Buffer.byteLength(text) > 48000) throw Object.assign(new Error('Requisição muito grande.'),{status:413});
  }
  try {
    const data = JSON.parse(text);
    if (!data || Array.isArray(data) || typeof data !== 'object') throw new Error();
    return data;
  } catch { throw Object.assign(new Error('Objeto JSON inválido.'),{status:400}); }
}
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml' };
const routes = new Set(['/', '/seguros', '/seguros/seguro-empresarial', '/seguros/seguro-empresarial/']);
const quoteRoutes = new Set(['/cotacao', '/cotacao/', '/cotacao/home', '/home']);
export const server = http.createServer(async (req, res) => {
  try {
    const host = req.headers.host || '';
    if (!/^(?:localhost|127\.0\.0\.1)(?::\d+)?$/.test(host)) { json(res,403,{error:'Host não permitido.'}); return; }
    const url = new URL(req.url, `http://${host}`);
    const pathname = decodeURIComponent(url.pathname);
    if (pathname.startsWith('/api/')) {
      if (req.headers.origin && req.headers.origin !== url.origin) { json(res,403,{error:'Origem não permitida.'}); return; }
      if (pathname === '/api/interno/session' && req.method === 'GET') {
        json(res,200,{autorizado:!!authorized(req,'internal')?.role,role:getSession(req)?.role||null}); return;
      }
      if (pathname === '/api/interno/login' && req.method === 'POST') {
        const response=internalLogin(res,await body(req));json(res,response.status||200,response);return;
      }
      if (pathname === '/api/cliente/vincular' && req.method === 'POST') {
        const response=await clientLogin(res,await body(req));json(res,response.status||200,response);return;
      }
      if (pathname === '/api/logout' && req.method === 'POST') {
        logout(res,req);json(res,200,{ok:true});return;
      }
      if (pathname === '/api/cliente/cadastro' && req.method === 'POST') {
        const s=getSession(req);if(s?.role!=='client') {json(res,401,{error:'Vínculo empresarial verificado obrigatório.'});return;}
        json(res,200,await runMotor({action:'cadastro',payload:{empresaId:s.empresaId,imovelId:s.imovelId}}));return;
      }
      if (pathname.startsWith('/api/interno/') && !authorized(req,'internal')) {
        json(res,401,{error:'Faça login no painel interno para acessar dados do Datathon.'});return;
      }
      if (pathname === '/api/interno/roteiros' && req.method === 'POST') {
        const data=await body(req);
        const input={empresaId:data.empresaId,imovelId:data.imovelId};
        const report=await runMotor(data.cotacaoPayload?
          {action:'analisar',payload:{...data.cotacaoPayload,...input}}:
          {action:'cadastro',payload:input});
        json(res,200,await newDraft(report,data));return;
      }
      if (pathname === '/api/interno/roteiros/aprovar' && req.method === 'POST') {
        json(res,200,approve(await body(req)));return;
      }
      if (pathname === '/api/interno/ligacoes' && req.method === 'POST') {
        json(res,200,await makeCall(await body(req),project));return;
      }
      if (pathname === '/api/interno/roteiros/status' && req.method === 'POST') {
        json(res,200,draftStatus((await body(req)).id));return;
      }
      if (pathname === '/api/contexto' && req.method === 'GET') {
        if (!authorized(req,'internal')) {json(res,401,{error:'Acesso interno necessário.'});return;}
        json(res,200,await runMotor({action:'contexto'})); return;
      }
      if (req.method !== 'POST') { json(res,405,{error:'Método não permitido.'}); return; }
      const data = await body(req);
      if (pathname === '/api/atividades/buscar') {
        if (typeof data.description !== 'string' || data.description.length > 2000) { json(res,422,{error:'Descreva a empresa em até 2.000 caracteres.'}); return; }
        const found = searchActivities(index,data.description,{mode:'description',limit:3});
        json(res,200,{...found,engine:'local-rules-tfidf-v2',catalogCount:catalog.activities.length}); return;
      }
      if (pathname === '/api/demo/empresa') {
        // Atalho de ID sem autenticação é EXCLUSIVO da demonstração local, nunca produção.
        if (process.env.BB_DEMO_ID_LOOKUP !== '1' ||
            !['127.0.0.1','::1','::ffff:127.0.0.1'].includes(req.socket.remoteAddress)) {
          json(res,403,{error:'Demonstração por ID desativada. Configure BB_DEMO_ID_LOOKUP=1 apenas no computador local.'}); return;
        }
        json(res,200,await runMotor({action:'demo_empresa',payload:data})); return;
      }
      if (pathname === '/api/cnae/perfil') { json(res,200,await runMotor({action:'perfil_cnae',payload:data})); return; }
      if (pathname === '/api/interno/relatorio-cnae') { json(res,200,await runMotor({action:'relatorio_cnae',payload:data})); return; }
      if (pathname === '/api/recomendacao/cadastro') { if(!authorized(req,'internal')){json(res,401,{error:'Acesso interno necessário.'});return;} json(res,200,await runMotor({action:'cadastro',payload:data})); return; }
      if (pathname === '/api/recomendacao') {
        const session=getSession(req);
        if(session?.role==='client'){data.empresaId=session.empresaId;data.imovelId=session.imovelId;}
        else if((data.empresaId||data.imovelId)&&session?.role!=='internal'){
          json(res,403,{error:'É necessário confirmar a identidade para reutilizar dados empresariais.'});return;
        }
        json(res,200,await runMotor({action:'analisar',payload:data}));return;
      }
      json(res,404,{error:'API não encontrada.'}); return;
    }
    if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405).end(); return; }
    const file = ['/interno','/interno/'].includes(pathname) ?
      (getSession(req)?.role==='internal' ? 'quote.html' : 'internal-login.html') :
      quoteRoutes.has(pathname) ? 'quote.html' : routes.has(pathname) ? 'index.html' : pathname.replace(/^\/+/, '');
    const resolved = path.resolve(root, file);
    if (!resolved.startsWith(root + path.sep) && resolved !== path.join(root, 'index.html')) { res.writeHead(403).end(); return; }
    const data = await readFile(resolved);
    res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-cache' });
    res.end(req.method === 'HEAD' ? undefined : data);
  } catch (error) {
    if (req.url?.startsWith('/api/')) json(res,error.status || 503,{error:error.message || 'Serviço indisponível.'});
    else res.writeHead(404, { 'Content-Type':'text/plain; charset=utf-8' }).end('Página não encontrada');
  }
});
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  server.listen(port,'127.0.0.1',() => console.log(`Formulário + motor MVP: http://localhost:${port}/cotacao`));
}
