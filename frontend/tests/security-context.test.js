import test from 'node:test';
import assert from 'node:assert/strict';
import { securityContextView } from '../public/security-context.js';

test('contexto distingue zero observado, ausência e uso na recomendação',()=>{
 const html=securityContextView({status:'PARCIAL',codigo_ibge:'3550308',motivo:'Sem referência comercial',aplicada_no_motor:false,indicadores:[{crime:'Roubo',meses_observados:12,ocorrencias_12m:0,taxa_por_100mil_habitantes:null,status:'PARCIAL'}]},null);
 assert.match(html,/>0<\/td>/);assert.match(html,/Não disponível/);assert.match(html,/complementares/);assert.match(html,/PENDENTE_AVALIACAO/);
});
test('conteúdo da fonte e avaliação é escapado antes de exibir',()=>{
 const html=securityContextView({status:'DISPONIVEL',motivo:'<script>alert(1)</script>',aplicada_no_motor:true,indicadores:[{crime:'<img src=x>',meses_observados:12}]},{status:'<svg>',indice_0_100:50,faixa:'alto'});
 assert.doesNotMatch(html,/<script>|<img|<svg>/);assert.match(html,/&lt;script&gt;/);assert.match(html,/foi usada/);
});
