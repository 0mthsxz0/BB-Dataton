import { dimensionEvidence } from './report-evidence.js';
const esc = x => String(x ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = x => x == null ? 'A confirmar' : Number(x).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const operations = {refrigeration:'Há mercadorias que precisam de refrigeração?',delivery:'A empresa realiza entregas de mercadorias?',homeOffice:'Há bens da empresa cedidos para trabalho em casa?',cash:'Há dinheiro ou valores mantidos neste local?',shoppingControls:'O shopping tem segurança própria, brigada, hidrantes e sprinklers?'};
const names = {ROUBO_FURTO_ARROMBAMENTO:'Roubo ou furto de bens mediante arrombamento',VENDAVAL_EVENTOS_CORRELATOS:'Vendaval e eventos correlatos',RESPONSABILIDADE_CIVIL_EMPREGADOR:'Responsabilidade civil empregador',QUEBRA_DE_VIDROS:'Quebra de vidros'};

export function initializeProductState(state, rules) {
  Object.assign(state,{priority:'equilibrada',termYears:'1',propertyRelation:'',propertyStatus:'',wallMaterial:''});
  for(const key of Object.keys(operations))state['op_'+key]='';
  for(const code of rules.adjustable){state['adjust_'+code]='';state['want_'+code]=false;}
  for(const extra of rules.optional)state['extra_'+extra.code]=false;
}

export function productPayload(state, rules, withPlan=false) {
  return {operations:Object.fromEntries(Object.keys(operations).map(k=>[k,state['op_'+k]==='yes'?true:state['op_'+k]==='no'?false:null])),
    termYears:Number(state.termYears||1),priority:state.priority||'equilibrada',propertyRelation:state.propertyRelation,
    propertyStatus:state.propertyStatus,wallMaterial:state.wallMaterial,
    indispensable:rules.adjustable.filter(c=>state['want_'+c]),
    ...(withPlan ? {selectedPlan:{892:'ESSENCIAL',893:'PRATICO',894:'TOTAL'}[state.planId],
      coverageAdjustments:{include:rules.adjustable.filter(c=>state['adjust_'+c]==='include'),exclude:rules.adjustable.filter(c=>state['adjust_'+c]==='exclude')},
      optionalCovers:rules.optional.filter(c=>state['extra_'+c.code]).map(c=>c.code)} : {})};
}

export function productFields(state, select) {
  return `<section class="risk-inventory"><h2>Seu imóvel e suas prioridades</h2><p>Campos sem confirmação preservam os sinais do cadastro. A triagem verifica condições do imóvel e o limite único básico de R$ 7,5 milhões.</p><div class="form-grid">
    ${select('propertyRelation','Sua relação com o imóvel',[['owner','Proprietário'],['tenant','Inquilino']],{required:false,placeholder:'A confirmar'})}
    ${select('propertyStatus','Situação atual do imóvel',[['REGULAR','Regular e em uso'],['EM_OBRA','Em construção, reforma ou reconstrução'],['CONDENADO','Condenado ou interditado']],{required:false,placeholder:'Usar cadastro / a confirmar'})}
    ${select('wallMaterial','Material predominante das paredes externas',[['ALVENARIA','Alvenaria'],['CONCRETO','Concreto'],['MADEIRA','Madeira'],['MATERIAL_COMBUSTIVEL','Outro material combustível']],{required:false,placeholder:'Usar cadastro / a confirmar'})}
    ${select('priority','O que você mais quer proteger?',[['equilibrada','Proteção equilibrada'],['patrimonio','Patrimônio'],['continuidade','Continuidade da operação'],['terceiros','Responsabilidades perante terceiros']])}
    ${select('termYears','Vigência desejada',[1,2,3,4,5].map(n=>[n,`${n} ${n===1?'ano':'anos'}`]))}</div>
    <p>O foco escolhido multiplica por 1,5 os pesos das necessidades correspondentes. Não altera o risco territorial nem cria um preço.</p></section>
    <section class="risk-inventory"><h2>Como sua empresa funciona</h2><p>Estas confirmações opcionais ajudam a avaliar adicionais. Estimativas do cadastro não substituem sua resposta.</p><div class="form-grid">${Object.entries(operations).filter(([k])=>k!=='shoppingControls'||state.shopping==='yes').map(([k,label])=>select('op_'+k,label,[['yes','Sim'],['no','Não']],{required:false,full:true,placeholder:'Ainda não confirmado'})).join('')}</div></section>`;
}

export function packageFields(result, state, rules) {
  const rec=result.recomendacao, pack=result.personalizacao.pacote;
  return `<section class="package-editor"><h2>Personalize o pacote escolhido</h2><p>As seis obrigatórias são mantidas. Ajustes das outras quatro e adicionais seguem a política do guia e dependem de aceitação oficial. Prático e Total permitem esses ajustes nesta simulação.</p>
    <div class="form-grid">${rules.adjustable.map(c=>`<div class="qfield"><label for="adjust_${c}">${esc(names[c])}</label><select id="adjust_${c}" name="adjust_${c}"><option value="" ${!state['adjust_'+c]?'selected':''}>Padrão do plano</option><option value="include" ${state['adjust_'+c]==='include'?'selected':''}>Incluir</option><option value="exclude" ${state['adjust_'+c]==='exclude'?'selected':''}>Excluir</option></select><label><input type="checkbox" aria-label="Considerar ${esc(names[c])} indispensável na recomendação" name="want_${c}" ${state['want_'+c]?'checked':''}> Considerar indispensável na recomendação</label></div>`).join('')}</div>
    <details><summary>Avaliar coberturas adicionais</summary><p>Marcar significa solicitar avaliação. Compatibilidade de atividade e limites continuam pendentes; adicionais não entram na aderência dos dez itens padrão.</p>${result.personalizacao.adicionais.map(x=>`<label class="optional-cover"><input type="checkbox" name="extra_${x.code}" ${state['extra_'+x.code]?'checked':''}> <span><strong>${esc(x.name)}</strong>${x.sugerida?' · Sugerida para avaliar':''}<small>${esc(x.motivo)} Planos: ${x.plans.join(', ')}.</small></span></label>`).join('')}</details>
    <button class="btn btn-outline" id="apply-package" type="button">Aplicar ajustes e recalcular</button><p id="package-status" role="status">${pack.coberturas.length} coberturas no pacote calculado · Aderência ${pack.aderencia_percentual.toFixed(1)}% · Vigência ${pack.vigencia_anos} ano(s).</p>
    <p>Recomendação automática: ${esc(rec.plano_recomendado)}. Pacote calculado: ${esc(pack.plano)}. Assistências permanecem fixas.</p></section>`;
}

export function personalizationView(result) {
  const p=result.personalizacao;if(!p)return '';
  const t=p.triagem,pack=p.pacote;
  return `<section class="personalization-result" aria-label="Pacote personalizado"><h2>${t.bloqueado?'Encaminhamento necessário':'Seu pacote e os próximos ajustes'}</h2>
    ${t.bloqueado?`<p class="quote-error">Indicação de contratação bloqueada na triagem. ${t.motivos.map(esc).join(' ')} A comparação abaixo serve apenas para análise técnica.</p>`:''}
    <p>Objeto básico estimado: <strong>${money(t.valor_objeto_basico_brl)}</strong>. ${t.objeto_completo?'Componentes informados.':'Há componentes sem confirmação; o valor pode estar incompleto.'} ${esc(t.observacao)}</p>
    <p>${pack.coberturas.length} coberturas · Vigência ${pack.vigencia_anos} ano(s) · Aderência do pacote ${pack.aderencia_percentual.toFixed(1)}%.</p>
    ${pack.lacunas_prioritarias.length?`<p class="quote-error">Lacunas prioritárias no pacote: ${pack.lacunas_prioritarias.map(esc).join(', ')}.</p>`:''}
    <details open><summary>Faixas para dimensionar a proteção</summary><p>Cenários experimentais, em reais. Não são limites aprovados. Coberturas para o mesmo bem não devem ser somadas como patrimônios independentes.</p><div class="audit-table-wrap"><table class="audit-table"><caption>Dimensionamento e evidência por cobertura</caption><thead><tr><th>Cobertura</th><th>Faixa mínima–máxima</th><th>Origem e confirmação</th></tr></thead><tbody>${Object.entries(result.dimensionamento).filter(([c])=>pack.coberturas.includes(c)).map(([,d])=>`<tr><th scope="row">${esc(d.nome)}</th><td>${money(d.faixa_valor_min)} – ${money(d.faixa_valor_max)}</td><td>${dimensionEvidence(d)}</td></tr>`).join('')}</tbody></table></div></details>
    ${p.adicionais.some(x=>x.sugerida)?`<h3>Adicionais pertinentes para avaliar</h3><ul>${p.adicionais.filter(x=>x.sugerida).map(x=>`<li><strong>${esc(x.name)}</strong>: ${esc(x.motivo)} ${x.permitida_no_plano?'Plano compatível com a política do guia.':'Requer Prático ou Total na política do guia.'}</li>`).join('')}</ul>`:''}
    <p>${esc(p.shopping.mensagem)} ${esc(p.assistencias.mensagem)}</p>
    <details><summary>Fontes e versão das regras do produto</summary><p>${esc(p.versaoRegras)}. ${esc(p.conciliacao)}</p><ul>${p.fontesRegras.map(s=>`<li>${s.url?`<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a>`:esc(s.title)} — ${esc(s.role)}${s.accessed?` · Consulta ${esc(s.accessed)}`:''}</li>`).join('')}</ul></details></section>`;
}
