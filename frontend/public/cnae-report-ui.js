import { cadastroRecommendationView } from './quote-engine.js';
import { voiceMarkup } from './voice-ui.js';

const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const fmt=(value,decimals=1)=>Number(value||0).toLocaleString('pt-BR',{minimumFractionDigits:decimals,maximumFractionDigits:decimals});
const money=value=>Number(value).toLocaleString('pt-BR',{style:'currency',currency:'BRL',maximumFractionDigits:0});
const PLAN={ESSENCIAL:'Essencial',PRATICO:'Prático',TOTAL:'Total'};
const FINANCE_FIELDS={
  contentsValue:'Bens no estabelecimento',equipmentValue:'Equipamentos',
  stockValue:'Estoque médio',payroll:'Folha mensal',monthlyExpenses:'Despesas fixas mensais',
  monthlyRevenue:'Faturamento mensal',rentValue:'Aluguel mensal'
};
export function cnaeReportView(report){
 const code=esc(report.cnae);
 const buttons='<div class="cnae-report-actions"><button type="button" class="btn btn-outline" id="cnae-report-back">Consultar outro CNAE</button><button type="button" class="btn btn-outline" id="cnae-report-download">Baixar relatório JSON</button></div>';
 if(report.tipo==='individual'){
   const r=report.relatorio;
   const key=[r.cadastro?.empresa_id,r.cadastro?.imovel_id].join('|');
   return '<section class="cnae-direct-report"><p class="result-eyebrow">Relatório direto por CNAE</p>'+
     '<h2>CNAE '+code+' · Único estabelecimento encontrado</h2>'+
     '<p>Como este código possui somente um estabelecimento na base autorizada, a análise é individual, calculada diretamente com o motor de recomendação.</p>'+
     cadastroRecommendationView(r)+voiceMarkup(key)+buttons+'</section>';
 }
 const sample=report.amostra||{},plans=report.planos||[],stats=report.indices||[];
 const values=Object.entries(report.medianasFinanceiras||{}).filter(([k,v])=>k in FINANCE_FIELDS&&v!=null);
 return '<section class="cnae-direct-report" aria-label="Relatório consolidado por CNAE">'+
   '<p class="result-eyebrow">Relatório gerado automaticamente · Base Datathon</p>'+
   '<h2>CNAE '+code+' · '+esc(report.descricao)+'</h2>'+
   '<p>O relatório foi calculado usando o motor de seguros em cada unidade cadastrada nesta atividade, sem precisar selecionar uma empresa.</p>'+
   '<div class="cnae-summary-grid">'+
     '<div><strong>'+esc(sample.empresas)+'</strong><span>Empresas no CNAE</span></div>'+
     '<div><strong>'+esc(sample.estabelecimentos)+'</strong><span>Estabelecimentos analisados</span></div>'+
     '<div><strong>'+esc(report.triagensBloqueadas)+'</strong><span>Triagens que exigem análise</span></div></div>'+
   '<section class="recommendation"><h3>Comparativo de planos recomendados</h3>'+
     '<p>Distribuição dos resultados individuais do motor. Não é uma recomendação contratual para uma empresa específica.</p>'+
     '<div class="cnae-plan-list">'+plans.map(p=>'<div class="cnae-plan-item">'+
       '<div class="cnae-plan-header"><strong>'+esc(PLAN[p.plano]||p.plano)+'</strong><span>'+fmt(p.percentual)+'% · '+esc(p.quantidade)+' unidades</span></div>'+
       '<div class="cnae-bar-track"><div class="cnae-bar-fill" style="width:'+Math.max(0,Math.min(100,Number(p.percentual)||0))+'%"></div></div></div>').join('')+'</div>'+
     '<p><strong>Plano mais frequente: '+esc(PLAN[report.planoMaisFrequente])+'</strong>. Este resultado descreve a amostra, não substitui a análise de um estabelecimento identificado.</p></section>'+
   '<section class="recommendation"><h3>Prioridades calculadas por cobertura</h3>'+
     '<p>Medianas dos quatro índices decisórios, sem interpretação como probabilidade de sinistro.</p>'+
     '<div class="cnae-stat-grid">'+stats.map(s=>'<div class="cnae-stat"><strong>'+esc(s.nome)+'</strong>'+
        '<span>Prioridade mediana: '+fmt(s.prioridadeMediana)+' pontos</span>'+
        '<span>Confiança mediana: '+fmt(s.confiancaMediana)+'%</span></div>').join('')+'</div></section>'+
   (values.length?'<section class="recommendation"><h3>Valores de referência da atividade</h3><p>Medianas, não valores confirmados da sua empresa.</p>'+
      '<div class="cnae-stat-grid">'+values.map(([key,v])=>'<div class="cnae-stat"><strong>'+esc(FINANCE_FIELDS[key])+'</strong><span>'+money(v)+'</span></div>').join('')+'</div></section>':'')+
   '<section class="recommendation"><h3>Metodologia e ressalvas</h3><p>'+esc(report.metodo)+'</p><ul>'+
      (report.avisos||[]).map(note=>'<li>'+esc(note)+'</li>').join('')+
     '</ul><p>Para fazer uma ligação sobre uma empresa específica, é necessário identificar e autorizar aquela empresa: o CNAE sozinho não determina o destinatário.</p></section>'+
   buttons+'</section>';
}
