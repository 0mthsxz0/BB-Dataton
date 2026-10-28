import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { securityRoute } from './security-api.mjs';

const root = path.resolve(fileURLToPath(new URL('./public/', import.meta.url)));
const port = Number(process.env.PORT || 4174);
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml' };
const routes = new Set(['/', '/seguros', '/seguros/seguro-empresarial', '/seguros/seguro-empresarial/']);
const quoteRoutes = new Set(['/cotacao', '/cotacao/', '/cotacao/home', '/home']);
export const server = http.createServer(async (req, res) => {
  if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405).end(); return; }
  try {
    const url = new URL(req.url, 'http://localhost');
    const pathname = decodeURIComponent(url.pathname);
    if (pathname.startsWith('/api/seguranca/')) { await securityRoute(req, res, url); return; }
    const file = quoteRoutes.has(pathname) ? 'quote.html' : routes.has(pathname) ? 'index.html' : pathname.replace(/^\/+/, '');
    const resolved = path.resolve(root, file);
    if (!resolved.startsWith(root + path.sep) && resolved !== path.join(root, 'index.html')) { res.writeHead(403).end(); return; }
    const data = await readFile(resolved);
    res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-cache' });
    res.end(req.method === 'HEAD' ? undefined : data);
  } catch { res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' }).end('Página não encontrada'); }
});
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  server.listen(port, '127.0.0.1', () => console.log(`Local: http://localhost:${port}`));
}
