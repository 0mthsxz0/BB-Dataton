import test from 'node:test';
import assert from 'node:assert/strict';
import {questionLabel,fullName} from '../public/language.js';
test('palavras-chave em destaque sem interpretar texto como HTML',()=>{const s=questionLabel('Há equipamentos eletrônicos <script>?');assert.match(s,/<strong class="question-keyword">equipamentos eletrônicos<\/strong>/);assert.ok(s.includes('&lt;script&gt;'));});
test('nomes de responsabilidade civil por extenso',()=>assert.equal(fullName('RC empregador e RC estabelecimento'),'Responsabilidade civil empregador e Responsabilidade civil estabelecimento'));
