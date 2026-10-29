import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('PF/PJ radio handlers use the multiple-element selector on form startup', async()=>{
  const src=await readFile(new URL('../public/quote.js',import.meta.url),'utf8');
  assert.match(src, /if\(step===0\)\{\$\$\('\[name=personType\]'\)\.forEach\(/);
  assert.doesNotMatch(src, /if\(step===0\)\{\$\('\[name=personType\]'\)\.forEach\(/);
});
