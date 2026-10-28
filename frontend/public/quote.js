import { createActivityIndex, searchActivities, normalize, isValidSelection } from './activity-search.js';

const $=(s,root=document)=>root.querySelector(s);
const $$=(s,root=document)=>[...root.querySelectorAll(s)];
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const LABELS=['Dados pessoais','Dados da empresa','Dados do imóvel','Planos','Cadastro e pagamento','Conclusão'];
const TITLES=[
  'Vamos iniciar a cotação do seu seguro empresarial. Primeiro, preencha alguns dados pessoais:',
  'Para finalizar, informe alguns dados da empresa e o que você espera do seguro:',
  'Agora precisamos saber o endereço da sua empresa:',
  'Conheça os planos e escolha a proteção para sua empresa.',
  'Revise seus dados e explore as opções de pagamento.',
  'Tudo pronto! Sua simulação foi concluída.'
];
let catalog,index,plans;
let step=0;
let completed=0;
let picker;
const state={personType:'pf',name:'',cnpj:'',birthDate:'',maritalStatus:'',phone:'',email:'',activityId:'',subactivityId:'',otherSubactivity:'',protection:'',shopping:'',cep:'',street:'',number:'',complement:'',district:'',city:'',uf:'',planId:new URLSearchParams(location.search).get('plano')||'',payment:'',installments:'1',paymentDay:'5',reviewed:false,description:''};

function selectedActivity(){return catalog.activities.find(a=>a.id===state.activityId);}
function selectedSubactivity(){return selectedActivity()?.subactivities.find(s=>s.id===state.subactivityId);}
function selectedPlan(){return plans.plans.find(p=>p.id===state.planId);}
function field(key,label,{type='text',required=true,full=false,autocomplete='off',placeholder='',maxlength='',help='',min='',max='',inputmode=''}={}){
  return `<div class="qfield ${full?'span-two':''}"><label for="${key}">${label}${required?'':' <span class="small-note">(opcional)</span>'}</label><input id="${key}" name="${key}" type="${type}" value="${esc(state[key])}" ${required?'required':''} autocomplete="${autocomplete}" ${placeholder?`placeholder="${esc(placeholder)}"`:''} ${maxlength?`maxlength="${maxlength}"`:''} ${inputmode?`inputmode="${inputmode}"`:''} ${min?`min="${min}"`:''} ${max?`max="${max}"`:''} ${help?`aria-describedby="${key}-help"`:''}>${help?`<small id="${key}-help">${help}</small>`:''}</div>`;
}
function selectField(key,label,choices,{required=true,full=false,placeholder='Selecione'}={}){
  return `<div class="qfield ${full?'span-two':''}"><label for="${key}">${label}</label><select id="${key}" name="${key}" ${required?'required':''}><option value="">${placeholder}</option>${choices.map(c=>{const v=Array.isArray(c)?c[0]:c,t=Array.isArray(c)?c[1]:c;return `<option value="${esc(v)}" ${String(state[key])===String(v)?'selected':''}>${esc(t)}</option>`;}).join('')}</select></div>`;
}

class ActivityPicker {
  constructor(root,onChoose){this.root=root;this.onChoose=onChoose;this.open=false;this.mode='name';this.query='';this.active=-1;this.rows=[];this.render();}
  render(){
    const selection=selectedActivity();
    this.root.innerHTML=`<div class="qfield activity-picker"><label id="activity-label" for="activity-search">Qual é a atividade econômica?</label><div class="activity-input-wrap"><input id="activity-search" type="search" autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="activity-options" aria-labelledby="activity-label" aria-describedby="activity-help" placeholder="Escolha, busque ou descreva sua empresa"><button class="activity-toggle" type="button" aria-label="Abrir lista de atividades" aria-expanded="false">⌄</button></div><small id="activity-help">Role a lista, digite o nome ou use a busca inteligente para contar como sua empresa funciona.</small><button type="button" class="text-link smart-shortcut" style="align-self:flex-start;border:0;background:none;color:var(--deep);padding:6px 0;font-size:11px">✦ Descrever minha empresa</button><div id="activity-panel" class="activity-panel hidden"><div class="activity-modes" role="group" aria-label="Modo de busca de atividade"><button type="button" data-mode="name" aria-pressed="true">Lista e nome</button><button type="button" data-mode="description" aria-pressed="false">✦ Busca inteligente</button></div><div id="activity-list-area"><ul id="activity-options" class="activity-options" role="listbox" aria-label="Atividades econômicas"></ul><p class="activity-count" aria-live="polite"></p></div><div class="intelligent-panel hidden" id="intelligent-panel"><div class="qfield"><label for="business-description">Como a sua empresa funciona?</label><textarea id="business-description" maxlength="2000" placeholder="Ex.: Preparo pizzas e refeições para vender aos clientes. Atendo no salão e também faço entregas.">${esc(state.description)}</textarea><small>Conte o que vende, produz ou faz, quem atende e como trabalha. Não inclua dados pessoais.</small></div><button class="btn" type="button" id="find-activity">Encontrar minha atividade</button><div id="intelligent-results" aria-live="polite"></div><p class="smart-status">Sugestões para você conferir. A busca não decide aceitação nem enquadramento contratual.</p></div></div>${selection?`<div class="selected-activity"><strong>Atividade escolhida</strong>${esc(selection.label)}</div>`:''}</div>`;
    this.input=$('#activity-search',this.root);
    this.list=$('#activity-options',this.root);
    this.input.value='';
    this.input.addEventListener('focus',()=>{if(this.mode==='name')this.setOpen(true);});
    this.input.addEventListener('input',()=>{this.query=this.input.value;this.mode='name';this.setOpen(true);this.updateMode();this.updateList();});
    this.input.addEventListener('keydown',e=>this.onKey(e));
    $('.activity-toggle',this.root).addEventListener('click',()=>{this.mode='name';this.setOpen(!this.open);this.updateMode();if(this.open)this.input.focus();});
    $('.smart-shortcut',this.root).addEventListener('click',()=>this.setMode('description'));
    $$('[data-mode]',this.root).forEach(b=>b.addEventListener('click',()=>this.setMode(b.dataset.mode)));
    $('#business-description',this.root).addEventListener('input',e=>{state.description=e.target.value;});
    $('#find-activity',this.root).addEventListener('click',()=>this.suggest());
    this.updateList();
  }
  setOpen(value){this.open=value;$('#activity-panel',this.root).classList.toggle('hidden',!value);this.input.setAttribute('aria-expanded',String(value&&this.mode==='name'));$('.activity-toggle',this.root).setAttribute('aria-expanded',String(value));if(!value)this.input.removeAttribute('aria-activedescendant');}
  setMode(mode){this.mode=mode;this.setOpen(true);this.updateMode();if(mode==='description')$('#business-description',this.root).focus();else this.input.focus();}
  updateMode(){$$('[data-mode]',this.root).forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===this.mode)));$('#activity-list-area',this.root).classList.toggle('hidden',this.mode!=='name');$('#intelligent-panel',this.root).classList.toggle('hidden',this.mode!=='description');this.input.setAttribute('aria-expanded',String(this.open&&this.mode==='name'));}
  updateList(){
    this.active=-1;
    this.rows=searchActivities(index,this.query,{limit:catalog.activities.length}).results;
    this.input.removeAttribute('aria-activedescendant');
    this.list.innerHTML=this.rows.length?this.rows.map(({activity:a},i)=>`<li class="activity-option" id="activity-option-${i}" role="option" tabindex="-1" aria-selected="${a.id===state.activityId}" data-index="${i}">${esc(a.label)}<small>${a.subactivities.length===1?'1 subatividade disponível':`${a.subactivities.length} subatividades disponíveis`}</small></li>`).join(''):'<li role="presentation" class="no-results">Não encontrei esse nome. Experimente outra palavra ou descreva sua empresa na busca inteligente.</li>';
    $('.activity-count',this.root).textContent=`${this.rows.length} de ${catalog.activities.length} atividades`;
    $$('[data-index]',this.list).forEach(b=>{b.addEventListener('click',()=>this.choose(Number(b.dataset.index)));b.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();this.choose(Number(b.dataset.index));}});});
  }
  choose(i){const row=this.rows[i];if(!row)return;this.setOpen(false);this.onChoose(row.activity,null);}
  onKey(e){
    if(e.key==='Escape'){this.setOpen(false);return;}
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();this.mode='name';this.setOpen(true);this.updateMode();this.active=Math.max(0,Math.min(this.rows.length-1,this.active+(e.key==='ArrowDown'?1:-1)));this.highlight();}
    if(e.key==='Enter'&&this.open&&this.mode==='name'){e.preventDefault();if(this.active>=0)this.choose(this.active);}
    if(e.key==='Tab')this.setOpen(false);
  }
  highlight(){$$('.activity-option',this.list).forEach((e,i)=>e.classList.toggle('active',i===this.active));const row=$(`#activity-option-${this.active}`,this.root);if(row){this.input.setAttribute('aria-activedescendant',row.id);row.scrollIntoView({block:'nearest'});}}
  suggest(){
    state.description=$('#business-description',this.root).value;
    const found=searchActivities(index,state.description,{mode:'description',limit:3});
    $('#intelligent-results',this.root).innerHTML=`${found.question?`<p class="suggestion-question">${esc(found.question)}</p>`:''}${found.results.map((r,i)=>`<article class="suggestion"><h3>${esc(r.activity.label)}</h3><p>${esc(r.reason)}.</p>${r.subactivity?`<p><strong>Subatividade sugerida:</strong> ${esc(r.subactivity.label)}</p><p>${esc(r.subactivityReason)}.</p>`:'<p>Escolha a subatividade após confirmar a atividade.</p>'}<button class="btn btn-outline" type="button" data-suggestion="${i}">${r.subactivity?'Usar atividade e subatividade':'Usar esta atividade'}</button></article>`).join('')}`;
    $$('[data-suggestion]',this.root).forEach(b=>b.addEventListener('click',()=>{const result=found.results[Number(b.dataset.suggestion)];this.onChoose(result.activity,result.subactivity);}));
  }
}

function render(){
  picker=null;
  document.title=`${LABELS[step]} · Cotação empresarial`;
  $('#quote-root').innerHTML=`<ol class="quote-progress" aria-label="Etapas da cotação">${LABELS.map((label,i)=>`<li><button type="button" data-step="${i}" aria-label="Etapa ${i+1}: ${label}" ${i===step?'aria-current="step"':''} ${i<step?'class="completed"':''} ${i>completed?'disabled':''}></button></li>`).join('')}</ol><p class="step-caption">Etapa ${step+1} de ${LABELS.length} · ${LABELS[step]}</p><h1 class="quote-title" id="form-title">${TITLES[step]}</h1><div id="form-errors" role="alert"></div><div id="step-content"></div>`;
  $$('[data-step]').forEach(b=>b.addEventListener('click',()=>go(Number(b.dataset.step))));
  const content=[personal,business,address,planStep,review,success][step]();
  $('#step-content').innerHTML=content;
  if(step<5){
    const form=$('#quote-form');
    form.addEventListener('input',remember);
    form.addEventListener('change',remember);
    form.addEventListener('submit',e=>{e.preventDefault();if(!form.reportValidity())return;if(!validateStep())return;completed=Math.max(completed,step+1);go(step+1);});
    $('#quote-back')?.addEventListener('click',()=>go(step-1));
  }
  if(step===0)$$('[name=personType]').forEach(r=>r.addEventListener('change',e=>{state.personType=e.target.value;state.cnpj='';state.birthDate='';state.maritalStatus='';render();}));
  if(step===1){
    picker=new ActivityPicker($('#activity-picker'),(activity,sub)=>{
      const changed=state.activityId!==activity.id;
      state.activityId=activity.id;
      if(changed){state.subactivityId='';state.otherSubactivity='';}
      if(sub)state.subactivityId=sub.id;
      else if(activity.subactivities.length===1)state.subactivityId=activity.subactivities[0].id;
      render();$('#subactivity-field')?.scrollIntoView({block:'nearest'});$('#subactivity-field input:checked')?.focus({preventScroll:true});
    });
    $$('[name=subactivityId]').forEach(r=>r.addEventListener('change',e=>{state.subactivityId=e.target.value;state.otherSubactivity='';render();}));
  }
  if(step===4){$('#payment')?.addEventListener('change',e=>{state.payment=e.target.value;render();});}
  if(step===5){$('#download-summary').addEventListener('click',downloadSummary);$('#restart-quote').addEventListener('click',()=>{Object.keys(state).forEach(k=>state[k]=typeof state[k]==='boolean'?false:'');state.personType='pf';state.installments='1';state.paymentDay='5';completed=0;go(0);});}
}
function form(body,button='Avançar'){return `<form id="quote-form" aria-labelledby="form-title">${body}<div class="quote-navigation"><button type="button" class="back-button" id="quote-back" ${step===0?'disabled':''}>← Voltar</button><button class="btn" type="submit">${button} →</button></div></form>`;}
function personal(){const pj=state.personType==='pj';const today=new Date().toISOString().slice(0,10);return form(`<fieldset class="person-types"><legend>Você está cotando como</legend><label><input type="radio" name="personType" value="pj" ${pj?'checked':''}> Pessoa Jurídica</label><label><input type="radio" name="personType" value="pf" ${!pj?'checked':''}> Pessoa Física</label></fieldset><div class="form-grid">${field('name',pj?'Razão social':'Nome completo',{full:true,autocomplete:pj?'organization':'name',maxlength:160})}${pj?field('cnpj','CNPJ da empresa',{full:true,placeholder:'00.000.000/0000-00',maxlength:18,inputmode:'numeric'}):field('birthDate','Data de nascimento',{type:'date',autocomplete:'bday',min:'1900-01-01',max:today})}${!pj?selectField('maritalStatus','Estado civil',['Solteiro(a)','Casado(a)','Separado(a)']):''}${field('phone','Celular',{type:'tel',autocomplete:'tel',placeholder:'(00) 00000-0000',maxlength:16,inputmode:'tel'})}${field('email','E-mail',{type:'email',autocomplete:'email',maxlength:160,full:pj})}</div>`);}
function business(){
  const activity=selectedActivity();
  const sub=activity?`<div class="qfield" id="subactivity-field"><span id="subactivity-label">Qual é a subatividade econômica?</span><div class="subactivity-options" role="radiogroup" aria-labelledby="subactivity-label">${activity.subactivities.map(s=>`<label class="subactivity-choice"><input type="radio" name="subactivityId" value="${esc(s.id)}" ${s.id===state.subactivityId?'checked':''} required><span>${esc(s.label)}</span></label>`).join('')}<label class="subactivity-choice"><input type="radio" name="subactivityId" value="other" ${state.subactivityId==='other'?'checked':''} required><span>Outra subatividade — quero especificar</span></label></div>${state.subactivityId==='other'?`<div class="other-search">${field('otherSubactivity','Especifique a subatividade',{full:true,maxlength:300})}</div><small>Esta descrição precisa de confirmação de enquadramento. Não é uma categoria aprovada automaticamente.</small>`:''}<p class="sub-description">Revise a atividade e a subatividade escolhidas, mesmo quando vierem de uma sugestão.</p></div>`:'<p class="sub-description">A lista de subatividades aparece depois que você escolhe a atividade econômica.</p>';
  return form(`<div class="quote-form"><div id="activity-picker"></div>${sub}<div class="form-grid">${selectField('protection','O que você deseja proteger?',[['both','Imóvel e conteúdo'],['building','Somente o imóvel'],['contents','Somente o conteúdo']],{full:true})}${selectField('shopping','Sua empresa está localizada em shopping center?',[['yes','Sim'],['no','Não']],{full:true})}</div><p class="catalog-note">${catalog.counts.activities} atividades do catálogo consultado em 28/10/2026. Os nomes foram escritos por extenso para facilitar a leitura. A escolha precisa refletir a atividade principal do negócio.</p></div>`);
}
function address(){return form(`<p class="quote-subtitle">Informe o endereço do local que você quer proteger.</p><div class="form-grid">${field('cep','CEP',{placeholder:'00000-000',maxlength:9,inputmode:'numeric',autocomplete:'postal-code'})}${field('number','Número',{maxlength:12,help:'Se não houver número, informe “sem número”.'})}${field('street','Endereço',{full:true,autocomplete:'address-line1',maxlength:200})}${field('complement','Complemento',{full:true,required:false,autocomplete:'address-line2',maxlength:100})}${field('district','Bairro',{maxlength:100})}${field('city','Cidade',{autocomplete:'address-level2',maxlength:100})}${selectField('uf','UF',['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'],{full:true})}</div><p class="catalog-note">O endereço é preenchido localmente. Nenhuma consulta de CEP ou envio à seguradora é realizado neste protótipo.</p>`,'Ver os planos');}
function planStep(){return form(`<p class="quote-subtitle">Os valores abaixo são referências públicas, não o resultado de uma precificação para os seus dados.</p><div class="qplans">${plans.plans.map(p=>`<label class="qplan"><span class="qplan-top"><input type="radio" name="planId" value="${p.id}" ${p.id===state.planId?'checked':''} required><strong>${esc(p.name)}</strong></span><p>${p.assistances} assistências + ${p.coverageCount} coberturas</p><div class="qplan-price">${esc(p.price)}<small> / mês*</small></div><details><summary>Ver itens associados ao plano</summary><ul>${plans.coverages.filter(c=>p.coverages.includes(c.id)).map(c=>`<li>${esc(c.name)}</li>`).join('')}</ul></details></label>`).join('')}</div><p class="catalog-note">*Preços de referência da página pública de 27/10/2026. O valor varia com o perfil e as condições do produto. A simulação local não calcula prêmio nem garante aceitação.</p>`,'Continuar');}
function summary({includeContact=false}={}){
  const activity=selectedActivity(),sub=selectedSubactivity(),plan=selectedPlan();
  return `<div class="quote-review"><h2>Seu resumo</h2><dl>${includeContact?`<dt>${state.personType==='pj'?'Empresa':'Nome'}</dt><dd>${esc(state.name)}</dd><dt>Contato</dt><dd>${esc(state.email)}<br>${esc(state.phone)}</dd>`:''}<dt>Atividade</dt><dd>${esc(activity?.label||'Não selecionada')}</dd><dt>Subatividade</dt><dd>${esc(sub?.label||state.otherSubactivity||'A confirmar')}</dd><dt>Proteção</dt><dd>${esc({both:'Imóvel e conteúdo',building:'Somente o imóvel',contents:'Somente o conteúdo'}[state.protection]||'')}</dd><dt>Localização</dt><dd>${esc(state.city)} / ${esc(state.uf)}</dd><dt>Plano</dt><dd>${esc(plan?.name||'')}</dd></dl></div>`;
}
function review(){return form(`${summary({includeContact:true})}<div class="form-grid">${selectField('payment','Como gostaria de pagar?',[['card','Cartão de crédito'],['debit','Débito em conta'],['boleto','Boleto bancário']],{full:true})}${selectField('installments','Quantidade de parcelas',[['1','À vista'],['2','2 parcelas'],['3','3 parcelas'],['4','4 parcelas'],['5','5 parcelas'],['6','6 parcelas'],['7','7 parcelas'],['8','8 parcelas'],['9','9 parcelas'],['10','10 parcelas'],['11','11 parcelas'],['12','12 parcelas']])}${selectField('paymentDay','Dia de vencimento',[['5','Dia 5'],['10','Dia 10'],['15','Dia 15'],['20','Dia 20'],['25','Dia 25']])}</div><p class="payment-note">Esta etapa demonstra a escolha de pagamento. Não solicita cartão, código de segurança ou dados bancários. Disponibilidade de parcelas, vencimentos e preço final precisam ser confirmados na contratação oficial.</p><label class="local-agreement"><input name="reviewed" type="checkbox" required ${state.reviewed?'checked':''}><span>Revisei as informações e quero concluir esta demonstração. Isso não contrata um seguro e não gera cobrança.</span></label>`,'Concluir demonstração');}
function success(){return `<div class="quote-success"><div class="success-icon" aria-hidden="true">✓</div><p>Você percorreu todas as etapas da demonstração. As informações foram mantidas somente na memória desta página.</p>${summary()}<p>Para obter uma cotação válida e contratar, utilize o canal oficial da BB Seguros. Os dados preenchidos aqui não são transferidos.</p><button class="btn" id="download-summary">Baixar resumo sem dados pessoais</button><a class="btn btn-outline" href="https://cotacaoseguroempresarial.bbseguros.com.br/home" target="_blank" rel="noopener noreferrer">Abrir cotação oficial ↗</a><p><button class="back-button" id="restart-quote">Começar novamente e limpar os dados</button></p></div>`;}

function remember(e){const t=e.target;if(!t.name||!(t.name in state))return;state[t.name]=t.type==='checkbox'?t.checked:t.value;if(t.name==='phone'){let v=t.value.replace(/\D/g,'').slice(0,11);if(v.length>2)v=`(${v.slice(0,2)}) ${v.slice(2)}`;if(v.replace(/\D/g,'').length>7)v=v.slice(0,-4)+'-'+v.slice(-4);t.value=v;state.phone=v;}if(t.name==='cep'){const v=t.value.replace(/\D/g,'').slice(0,8);t.value=v.length>5?v.slice(0,5)+'-'+v.slice(5):v;state.cep=t.value;}}
function fail(message){$('#form-errors').innerHTML=`<p class="quote-error">${esc(message)}</p>`;$('#form-errors').scrollIntoView({block:'nearest'});return false;}
function validCnpj(value){const digits=value.replace(/\D/g,'');if(digits.length!==14||/^(\d)\1+$/.test(digits))return false;function digit(base){let weight=base.length-7;let sum=0;for(const c of base){sum+=Number(c)*weight--;if(weight===1)weight=9;}const rest=sum%11;return rest<2?'0':String(11-rest);}return digit(digits.slice(0,12))===digits[12]&&digit(digits.slice(0,13))===digits[13];}
function validateStep(){
  if(step===0){if(state.name.trim().length<3)return fail('Informe o nome ou razão social com pelo menos três caracteres.');if(state.personType==='pj'&&!validCnpj(state.cnpj))return fail('Confira o CNPJ da empresa.');if(![10,11].includes(state.phone.replace(/\D/g,'').length))return fail('Informe um telefone com DDD e número completo.');}
  if(step===1){if(!selectedActivity())return fail('Escolha uma atividade na lista ou confirme uma sugestão da busca inteligente.');if(state.subactivityId==='other'){if(state.otherSubactivity.trim().length<4)return fail('Descreva a outra subatividade para revisão.');}else if(!isValidSelection(catalog,state.activityId,state.subactivityId))return fail('Escolha uma subatividade vinculada à atividade selecionada.');}
  if(step===2&&state.cep.replace(/\D/g,'').length!==8)return fail('Confira o CEP com oito números.');
  if(step===3&&!selectedPlan())return fail('Escolha um plano para continuar.');
  return true;
}
function go(value,{historyEntry=true}={}){if(value<0||value>Math.min(completed,5))return;step=value;render();if(historyEntry)history.pushState({quoteStep:step},'',`/cotacao?etapa=${step+1}`);$('#quote-main').scrollIntoView({block:'start'});$('#quote-main').focus({preventScroll:true});}
function downloadSummary(){const a=selectedActivity(),s=selectedSubactivity();const result={demonstracao:true,contratacao:false,atividade:{codigo:a.id,nome:a.label},subatividade:s?{codigo:s.id,nome:s.label}:{codigo:null,nome:state.otherSubactivity,confirmacaoPendente:true},protecao:state.protection,plano:selectedPlan()?.name,pagamentoPreferido:state.payment,observacao:'Não é cotação oficial. Sem dados pessoais, bancários, endereço ou descrição livre.'};const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='resumo-demonstracao-empresarial.json';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
document.addEventListener('pointerdown',e=>{if(picker?.open&&!picker.root.contains(e.target))picker.setOpen(false);});
window.addEventListener('popstate',e=>{const target=e.state?.quoteStep??0;go(Math.min(target,completed),{historyEntry:false});});

try{
  const responses=await Promise.all([fetch('/activities.json'),fetch('/plans.json')]);
  if(responses.some(r=>!r.ok))throw new Error('Falha ao carregar o catálogo.');
  [catalog,plans]=await Promise.all(responses.map(r=>r.json()));
  index=createActivityIndex(catalog);
  if(!plans.plans.some(p=>p.id===state.planId))state.planId='';
  history.replaceState({quoteStep:0},'',state.planId?`/cotacao?plano=${state.planId}`:'/cotacao');
  render();
}catch(error){$('#quote-root').innerHTML=`<div class="quote-load-error" role="alert"><h1>Não foi possível abrir o formulário.</h1><p>${esc(error.message)}</p><button class="btn" id="retry-catalog">Tentar novamente</button></div>`;$('#retry-catalog').addEventListener('click',()=>location.reload());}
