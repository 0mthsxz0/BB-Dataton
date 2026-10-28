import test from 'node:test';
import assert from 'node:assert/strict';
import { dimensionEvidence, indexEvidence } from '../public/report-evidence.js';

test('origin cell exposes actual numbers, CSV fields and derivation rather than only a conclusion',()=>{
  const html=dimensionEvidence({justificativa:'Cenário de teste',evidencias:[{rotulo:'Bens atribuídos',valor:50000,unidade:'BRL',origem:'Cadastro BB/Datathon',arquivo:'bens_cadastrados.csv',campo:'bens_ponderados',campos_origem:['valor_cadastrado','probabilidade_bem_no_imovel_referencia'],transformacao_origem:'Soma de valor × vínculo',estado:'CADASTRO_ESTIMATIVA',chave:{imovel_id:'IMO_TESTE'}}],dados_calculo:{bens_ponderados:50000,estoque_medio:10000},confianca:.8});
  for(const text of ['50.000,00','10.000,00','bens_cadastrados.csv','valor_cadastrado','probabilidade_bem_no_imovel_referencia','Soma de valor × vínculo','IMO_TESTE'])assert.ok(html.includes(text));
});

test('index report shows raw external values and period, safely escaping source content',()=>{
  const s={nome:'Teste',prioridade:30,classe:'Baixa',prioridade_min:10,prioridade_max:50,confianca:.4,valor_exposto_brl:null,risco_evento_relativo:.3,impacto_normalizado:.5,vulnerabilidade:.5,
    explicacao_contextual:'Contexto',leitura_contextual:'Dados desta unidade',formula:'Fórmula',decomposicao:{base_pontos:30,interacao_pontos:0,efeito_limite_pontos:0},fatores_evento:[],fator_impacto:{},fator_vulnerabilidade:{},
    referencia_publica:{fonte:'https://sidra.ibge.gov.br/tabela/8510',periodo:'2021',granularidade:'MUNICIPIO',modo_acesso:'Snapshot local; sem consulta ao vivo',condicao:'Referência presente',dados:{taxa_furto_domicilios:.04,descricao_nr4:'<script>alert(1)</script>'},vinculo:{municipio:'Cidade de teste'}},respostas_utilizadas:{securityControls:null}};
  const html=indexEvidence('TESTE',s);
  for(const text of ['Dados desta unidade','2021','valor bruto: 0.04','4%','Cidade de teste','sidra.ibge.gov.br','Não disponível'])assert.ok(html.includes(text));
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(!indexEvidence('TESTE',{...s,referencia_publica:null}).includes('href="https://sidra'));
  const blocked=indexEvidence('TESTE',{...s,qualidade_seguranca:{status:'INCOMPATIVEL',data_analise:'2026-10-28',politica:'seguranca-1.0',motivos:['Vitimização domiciliar excluída <teste>']}});
  for(const text of ['Base territorial: Dados incompatíveis','Vitimização domiciliar excluída &lt;teste&gt;','2026-10-28','não é precisão estatística'])assert.ok(blocked.includes(text));
});
