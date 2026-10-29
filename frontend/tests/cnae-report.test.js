import test from 'node:test';
import assert from 'node:assert/strict';
import { cnaeReportView } from '../public/cnae-report-ui.js';

test('relatório do CNAE abre com distribuição, não inventa identificação individual',()=>{
  const result={
    tipo:'setorial',cnae:'4771701',descricao:'Farmácia <Teste>',
    amostra:{empresas:118,estabelecimentos:129},triagensBloqueadas:2,
    planos:[{plano:'ESSENCIAL',quantidade:40,percentual:31.0},{plano:'PRATICO',quantidade:50,percentual:38.8},{plano:'TOTAL',quantidade:39,percentual:30.2}],
    planoMaisFrequente:'PRATICO',
    indices:[{codigo:'ROUBO_FURTO_ARROMBAMENTO',nome:'Roubo e furto',prioridadeMediana:44.3,confiancaMediana:45.1}],
    medianasFinanceiras:{stockValue:20000},
    avisos:['Sem cotação oficial'],metodo:'Análise independente por unidade'
  };
  const html=cnaeReportView(result);
  assert.match(html,/118/);
  assert.match(html,/129/);
  assert.match(html,/Prático/);
  assert.match(html,/Relatório consolidado por CNAE/);
  assert.doesNotMatch(html,/<Teste>/);
  assert.doesNotMatch(html,/voice-send/);
  assert.match(html,/Baixar relatório JSON/);
});
