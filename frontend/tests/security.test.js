import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { securityRoute } from '../security-api.mjs';
import { relativeNeed, coverageSuggestion, matchingMunicipality } from '../public/security.js';

test('ausência de índice não vira zero nem indicação de seguro', () => {
  assert.equal(relativeNeed(null, 100000, 'sim', 'interno'), null);
  assert.equal(relativeNeed(50, '', 'sim', 'interno'), null);
  assert.equal(relativeNeed(50, 100000, '', 'interno'), null);
  assert.equal(relativeNeed(101, 100000, 'sim', 'interno'), null);
  assert.deepEqual(coverageSuggestion({ indice_roubo_0_100: null }, []), []);
});

test('cenários combinam valor, risco e hipóteses separadas de CRITIC', () => {
  const a = relativeNeed(50, 100000, 'sim', 'interno', true);
  const b = relativeNeed(50, 200000, 'sim', 'interno', true);
  assert.equal(b.points, 2 * a.points);
  assert.equal(a.garageFactor, 0.85);
  assert.match(a.version, /hipotese/);
  assert.deepEqual(coverageSuggestion({ indice_roubo_0_100: 90, uso_empresarial_validado: true }, [
    {name: 'A', coverages: []}, {name: 'B', coverages: ['10932']}]), ['B']);
});

test('contexto SINESP sem validação empresarial não pontua bens nem sugere plano', () => {
  assert.equal(relativeNeed(90, 100000, 'sim', 'interno'), null);
  assert.deepEqual(coverageSuggestion({ indice_roubo_0_100: 90, uso_empresarial_validado: false }, [
    { name: 'Plano teste', coverages: ['10932'] }]), []);
});

test('município exige nome completo e UF, aceita acentos e evita ambiguidade', () => {
  const candidates = [{codigo_ibge: '3550308', municipio: 'São Paulo', uf: 'SP'}];
  assert.equal(matchingMunicipality('sao paulo', 'SP', candidates).codigo_ibge, '3550308');
  assert.equal(matchingMunicipality('sao', 'SP', candidates), null);
  assert.equal(matchingMunicipality('sao paulo', 'RJ', candidates), null);
  assert.equal(matchingMunicipality('sao paulo', 'SP', [...candidates, ...candidates]), null);
});

test('API valida parâmetros, mantém índice nulo e informa base indisponível', async t => {
  const queries = [];
  const query = async params => {
    queries.push(params);
    if (params.code) return {status:200,dados:{codigo_ibge: params.code, indice_roubo_0_100:null}};
    return {status:503,erro:'Base indisponível.'};
  };
  const server = http.createServer((req, res) => securityRoute(req, res, new URL(req.url, 'http://localhost'), query));
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => { server.closeAllConnections(); return new Promise(resolve => server.close(resolve)); });
  const base = `http://127.0.0.1:${server.address().port}`;
  const response = await fetch(base + '/api/seguranca/3550308');
  assert.equal(response.status, 200);
  assert.equal((await response.json()).indice_roubo_0_100, null);
  assert.equal((await fetch(base + '/api/seguranca/municipios?uf=SP&q=Sao')).status, 503);
  assert.equal((await fetch(base + '/api/seguranca/municipios?uf=INVALIDA')).status, 400);
  assert.equal((await fetch(base + '/api/seguranca/invalid')).status, 404);
  assert.equal((await fetch(base + '/api/seguranca/3550308', {method:'POST'})).status, 405);
  assert.deepEqual(Object.keys(queries[0]).sort(), ['code','q','uf']);
});
