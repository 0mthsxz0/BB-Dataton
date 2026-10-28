import { execFile } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const project = path.resolve(fileURLToPath(new URL('../', import.meta.url)));
const candidates = [path.join(project, '.venv/Scripts/python.exe'), path.join(project, '.venv/bin/python'), path.resolve(project, '../.venvs/bb-dataton/bin/python')];
let running = 0;

export function querySecurity({ code, uf, q = '' }) {
  if (running >= 4) return Promise.resolve({ status: 503, erro: 'Consulta ocupada; tente novamente.' });
  const python = process.env.BB_PYTHON || candidates.find(existsSync) || (process.platform === 'win32' ? 'python' : 'python3');
  const database = process.env.BB_SEGURANCA_DB || path.join(project, 'data/seguranca/seguranca.sqlite');
  const args = ['-m', 'seguranca', '--banco', database, 'consultar'];
  if (code) args.push('--codigo', code);
  else args.push('--uf', uf, '--busca', q);
  running++;
  return new Promise(resolve => {
    execFile(python, args, { cwd: project, env: { ...process.env, PYTHONUTF8: '1' }, timeout: 15000, maxBuffer: 2 * 1024 * 1024 }, (error, stdout) => {
      running--;
      try {
        const result = JSON.parse(stdout);
        if (![200, 400, 404, 503].includes(result.status)) throw new Error('Resposta inválida');
        resolve(result);
      } catch {
        resolve({ status: 503, erro: error?.killed ? 'Consulta excedeu o tempo limite.' : 'Base de segurança indisponível.' });
      }
    });
  });
}

export async function securityRoute(req, res, url, query = querySecurity) {
  const send = (status, data) => {
    res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
    res.end(JSON.stringify(data));
  };
  if (req.method !== 'GET') { send(405, { erro: 'Use GET.' }); return; }
  const code = url.pathname.match(/^\/api\/seguranca\/(\d{7})$/)?.[1];
  const uf = url.searchParams.get('uf') || '';
  const q = url.searchParams.get('q') || '';
  if (!code && url.pathname !== '/api/seguranca/municipios') { send(404, { erro: 'Consulta não encontrada.' }); return; }
  if (!code && (!/^[A-Z]{2}$/.test(uf) || q.length > 100)) { send(400, { erro: 'Informe UF e busca de até 100 caracteres.' }); return; }
  try {
    const result = await query({ code, uf, q });
    send(result.status, result.status === 200 ? result.dados : { erro: result.erro });
  } catch {
    send(503, { erro: 'Base de segurança indisponível.' });
  }
}
