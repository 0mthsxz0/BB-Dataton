import { fullName, questionLabel } from './language.js';
import { voiceMarkup, bindVoice } from './voice-ui.js';
import { cnaeReportView } from './cnae-report-ui.js';
import { customerRecommendationView, customerReport } from './journeys.js';
import { initializeProductState, productPayload, productFields, packageFields, optionalFields, syncPackageState, packageCount } from './product-ui.js';
import { api, riskFields, riskPayload, employeePresence, syncEmployeeExposure, recommendationView, baseFields, cadastroRecommendationView } from './quote-engine.js';
import { createActivityIndex, searchActivities, normalize, isValidSelection } from './activity-search.js';

const $=(s,root=document)=>root.querySelector(s);
const $$=(s,root=document)=>[...root.querySelectorAll(s)];
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const internal=location.pathname.startsWith('/interno');
const journeyPath=internal?'/interno':'/cotacao';
const LABELS=['Dados pessoais','Dados da empresa','Dados do imóvel','Proteção','Planos','Cadastro e pagamento','Conclusão'];
const TITLES=[
  'Vamos iniciar a cotação do seu seguro empresarial. Primeiro, preencha alguns dados pessoais:',
  'Para finalizar, informe alguns dados da empresa e o que você espera do seguro:',
  'Agora precisamos saber o endereço da sua empresa:',
  'Vamos entender o que sua empresa precisa proteger.',
  'Conheça os planos e escolha a proteção para sua empresa.',
  'Revise seus dados e explore as opções de pagamento.',
  'Tudo pronto! Sua simulação foi concluída.'
];
let catalog,index,plans,questionnaire,baseContext,productRules;
let recommendation=null,busy=false;
let cadastroRecommendation=null,cadastroLoading=false,cadastroError='',cadastroRevision=0;
let cnaeReport=null;
let step=internal?1:0;
let completed=internal?1:0;
let picker;
let profileRevision=0,profileLoading=false,profileTimer;

const state={personType:'pf',name:'',cnpj:'',birthDate:'',maritalStatus:'',phone:'',email:'',activityId:'',subactivityId:'',otherSubactivity:'',protection:'',shopping:'',cep:'',street:'',number:'',complement:'',district:'',city:'',uf:'',planId:new URLSearchParams(location.search).get('plano')||'',payment:'',installments:'1',paymentDay:'5',reviewed:false,description:'',sourceKey:'',profileFields:[],prefilledFields:[],cnaeProfile:null,units:'',cnae:'',contentsValue:'',equipmentValue:'',stockValue:'',buildingValue:'',glassValue:'',glassCount:'',employees:'',payroll:'',monthlyExpenses:'',monthlyRevenue:'',rentValue:'',securityControls:'',portableGoods:'',roofMaintained:'',exposedAssets:'',hasEmployees:'',hazardousWork:'',hasGlass:'',glassExposed:''};

function selectedActivity(){return catalog.activities.find(a=>a.id===state.activityId);}
function selectedSubactivity(){return selectedActivity()?.subactivities.find(s=>s.id===state.subactivityId);}
function selectedPlan(){return plans.plans.find(p=>p.id===state.planId);}
function field(key,label,{type='text',required=true,full=false,autocomplete='off',placeholder='',maxlength='',help='',min='',max='',inputmode='',increment='any'}={}){
  return `<div class="qfield ${full?'span-two':''}"><label for="${key}">${questionLabel(label)}${required?'':' <span class="small-note">(opcional)</span>'}</label><input id="${key}" name="${key}" type="${type}" ${type==='number'?`step="${esc(increment)}"`:''} value="${esc(state[key])}" ${required?'required':''} autocomplete="${autocomplete}" ${placeholder?`placeholder="${esc(placeholder)}"`:''} ${maxlength?`maxlength="${maxlength}"`:''} ${inputmode?`inputmode="${inputmode}"`:''} ${min?`min="${min}"`:''} ${max?`max="${max}"`:''} ${help?`aria-describedby="${key}-help"`:''}>${help?`<small id="${key}-help">${help}</small>`:''}</div>`;
}
function selectField(key,label,choices,{required=true,full=false,placeholder='Selecione'}={}){
  return `<div class="qfield ${full?'span-two':''}"><label for="${key}">${questionLabel(label)}</label><select id="${key}" name="${key}" ${required?'required':''}><option value="">${placeholder}</option>${choices.map(c=>{const v=Array.isArray(c)?c[0]:c,t=Array.isArray(c)?c[1]:c;return `<option value="${esc(v)}" ${String(state[key])===String(v)?'selected':''}>${esc(t)}</option>`;}).join('')}</select></div>`;
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
  async suggest(){
    state.description=$('#business-description',this.root).value;
    const button=$('#find-activity',this.root);button.disabled=true;button.textContent='Buscando no catálogo…';
    let found;
    try { found=await api('/api/atividades/buscar',{description:state.description}); }
    catch(error){$('#intelligent-results',this.root).innerHTML=`<p class="quote-error">${esc(error.message)}</p>`;return;}
    finally {button.disabled=false;button.textContent='Encontrar minha atividade';}
    if(!this.root.isConnected)return;
    $('#intelligent-results',this.root).innerHTML=`${found.question?`<p class="suggestion-question">${esc(found.question)}</p>`:''}${found.results.map((r,i)=>`<article class="suggestion"><h3>${esc(r.activity.label)}</h3><p>${esc(r.reason)}.</p>${r.subactivity?`<p><strong>Subatividade sugerida:</strong> ${esc(r.subactivity.label)}</p><p>${esc(r.subactivityReason)}.</p>`:'<p>Escolha a subatividade após confirmar a atividade.</p>'}<button class="btn btn-outline" type="button" data-suggestion="${i}">${r.subactivity?'Usar atividade e subatividade':'Usar esta atividade'}</button></article>`).join('')}`;
    $$('[data-suggestion]',this.root).forEach(b=>b.addEventListener('click',()=>{const result=found.results[Number(b.dataset.suggestion)];this.onChoose(result.activity,result.subactivity,result.requiresSubactivityConfirmation);}));
  }
}

function render(){
  picker=null;
  updateReportLayout();
  document.title=`${LABELS[step]} · Cotação empresarial`;
  $('#quote-root').innerHTML=`<ol class="quote-progress" aria-label="Etapas da cotação">${LABELS.map((label,i)=>`<li><button type="button" data-step="${i}" aria-label="Etapa ${i+1}: ${label}" ${i===step?'aria-current="step"':''} ${i<step?'class="completed"':''} ${i>completed?'disabled':''}></button></li>`).join('')}</ol><p class="step-caption">Etapa ${step+1} de ${LABELS.length} · ${LABELS[step]}</p><h1 class="quote-title" id="form-title">${TITLES[step]}</h1><div id="form-errors" role="alert"></div><div id="step-content"></div>`;
  $$('[data-step]').forEach(b=>b.addEventListener('click',()=>go(Number(b.dataset.step))));
  const direct=internal&&step===1&&cnaeReport;
  const content=direct?cnaeReportView(cnaeReport):[personal,business,address,protectionStep,planStep,review,success][step]();
  $('#step-content').innerHTML=content;
  if(direct){
    document.title='Relatório do CNAE '+cnaeReport.cnae+' · BB-Datathon';
    $('#form-title').textContent='Relatório automático da atividade econômica';
    $('#cnae-report-back').addEventListener('click',()=>{
      cnaeReport=null;cadastroRecommendation=null;state.sourceKey='';render();
      $('#cnae')?.focus({preventScroll:true});
    });
    $('#cnae-report-download').addEventListener('click',()=>{
      const blob=new Blob([JSON.stringify(cnaeReport,null,2)],{type:'application/json'});
      const url=URL.createObjectURL(blob),link=document.createElement('a');
      link.href=url;link.download='relatorio-cnae-'+cnaeReport.cnae+'.json';
      document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
    });
    if(cnaeReport.tipo==='individual'){
      const r=cnaeReport.relatorio;
      bindVoice(r.cadastro.empresa_id+'|'+r.cadastro.imovel_id);
    }
    return;
  }
  if(step<6){
    const form=$('#quote-form');
    form.addEventListener('input',remember);
    form.addEventListener('change',remember);
    form.addEventListener('submit',async e=>{e.preventDefault();if(busy||profileLoading||!form.reportValidity()||!validateStep())return;
      if(step===3){busy=true;const submit=form.querySelector('[type=submit]');submit.textContent=internal?'Calculando os índices…':'Preparando sua recomendação…';form.setAttribute('aria-busy','true');const controls=[...document.querySelectorAll('#quote-root button,#quote-form input,#quote-form select')];controls.forEach(c=>{c.dataset.wasDisabled=String(c.disabled);c.disabled=true;});
        try{recommendation=await api('/api/recomendacao',{...riskPayload(state,questionnaire),...productPayload(state,productRules)});syncPackageState(recommendation,state,productRules);}catch(error){fail(error.message);return;}finally{busy=false;controls.forEach(c=>{c.disabled=c.dataset.wasDisabled==='true';});submit.textContent='Calcular recomendação →';form.removeAttribute('aria-busy');}
      }
      if(step===4 && !await applyPackage())return;
      completed=Math.max(completed,step+1);go(step+1);});
    $('#quote-back')?.addEventListener('click',()=>go(step-1));
  }
  if(step===0){$$('[name=personType]').forEach(r=>r.addEventListener('change',e=>{state.personType=e.target.value;state.cnpj='';state.birthDate='';state.maritalStatus='';render();}));$('#verify-client')?.addEventListener('click',verifyClient);}
  if(step===1){
    picker=new ActivityPicker($('#activity-picker'),(activity,sub,requireSubactivityConfirmation=false)=>{
      invalidate();
      const changed=state.activityId!==activity.id;
      state.activityId=activity.id;
      if(changed){state.subactivityId='';state.otherSubactivity='';}
      if(requireSubactivityConfirmation)state.subactivityId='';
      else if(sub)state.subactivityId=sub.id;
      else if(activity.subactivities.length===1)state.subactivityId=activity.subactivities[0].id;
      render();$('#subactivity-field')?.scrollIntoView({block:'nearest'});$('#subactivity-field input:checked')?.focus({preventScroll:true});
    });
    $('#load-cnae-profile')?.addEventListener('click',requestProfile);
    $('#load-base')?.addEventListener('click',async()=>{const b=$('#load-base');b.disabled=true;$('#base-status').textContent='Carregando estabelecimentos…';try{baseContext=await api('/api/contexto');render();}catch(error){$('#base-status').textContent=error.message;b.disabled=false;}});
    $('#sourceKey')?.addEventListener('change',e=>{state.sourceKey=e.target.value;resetUnitInputs();const entry=baseContext?.estabelecimentos.find(r=>r.empresaId+'|'+r.imovelId===state.sourceKey);if(entry){state.city=entry.city;state.uf=entry.uf;}state.cnae='';invalidate();requestCadastro();});
    updateCadastroView();
    $$('[name=subactivityId]').forEach(r=>r.addEventListener('change',e=>{state.subactivityId=e.target.value;state.otherSubactivity='';render();}));
  }
  if(step===4){$('#apply-package')?.addEventListener('click',()=>applyPackage());if(internal)bindVoice(state.sourceKey,()=>({...riskPayload(state,questionnaire),...productPayload(state,productRules)}));}
  if(step===5){$('#payment')?.addEventListener('change',e=>{state.payment=e.target.value;render();});}
  if(step===6){$('#download-summary').addEventListener('click',downloadSummary);$('#restart-quote').addEventListener('click',()=>{Object.keys(state).forEach(k=>state[k]=typeof state[k]==='boolean'?false:'');initializeProductState(state,productRules);state.personType='pf';state.installments='1';state.paymentDay='5';recommendation=null;cadastroRecommendation=null;cadastroLoading=false;cadastroError='';cadastroRevision++;state.profileFields=[];state.prefilledFields=[];state.cnaeProfile=null;profileRevision++;completed=internal?1:0;go(internal?1:0);});}
}
function form(body,button='Avançar'){return `<form id="quote-form" aria-labelledby="form-title">${body}<div class="quote-navigation"><button type="button" class="back-button" id="quote-back" ${step===0?'disabled':''}>← Voltar</button><button class="btn" type="submit">${button} →</button></div></form>`;}
function personal(){const pj=state.personType==='pj';const today=new Date().toISOString().slice(0,10);return form(`<fieldset class="person-types"><legend>Você está cotando como</legend><label><input type="radio" name="personType" value="pj" ${pj?'checked':''}> Pessoa Jurídica</label><label><input type="radio" name="personType" value="pf" ${!pj?'checked':''}> Pessoa Física</label></fieldset><div class="form-grid">${field('name',pj?'Razão social':'Nome completo',{full:true,autocomplete:pj?'organization':'name',maxlength:160})}${pj?field('cnpj','CNPJ da empresa',{full:true,placeholder:'00.000.000/0000-00',maxlength:18,inputmode:'numeric'}):field('birthDate','Data de nascimento',{type:'date',autocomplete:'bday',min:'1900-01-01',max:today})}${!pj?selectField('maritalStatus','Estado civil',['Solteiro(a)','Casado(a)','Separado(a)']):''}${field('phone','Celular',{type:'tel',autocomplete:'tel',placeholder:'(00) 00000-0000',maxlength:16,inputmode:'tel'})}${field('email','E-mail',{type:'email',autocomplete:'email',maxlength:160,full:pj})}</div>${pj?'<section class="client-lookup"><h2>Já tem cadastro no banco?</h2><p>Confirme seu vínculo para aproveitar os dados existentes e ver sua recomendação preliminar. Dados não confirmados serão solicitados no formulário. O CNAE identifica uma atividade, não uma empresa.</p><label for="client-access-code">Código de verificação (demonstração)</label><input type="password" id="client-access-code" minlength="8" maxlength="128" autocomplete="off" placeholder="Código de acesso autorizado"><button type="button" class="btn btn-outline" id="verify-client">Verificar cadastro e recomendar</button><div id="client-status" role="status"></div></section>':''}`);}
function business(){
  const activity=selectedActivity();
  const sub=activity?`<div class="qfield" id="subactivity-field"><span id="subactivity-label">Qual é a subatividade econômica?</span><div class="subactivity-options" role="radiogroup" aria-labelledby="subactivity-label">${activity.subactivities.map(s=>`<label class="subactivity-choice"><input type="radio" name="subactivityId" value="${esc(s.id)}" ${s.id===state.subactivityId?'checked':''} required><span>${esc(s.label)}</span></label>`).join('')}<label class="subactivity-choice"><input type="radio" name="subactivityId" value="other" ${state.subactivityId==='other'?'checked':''} required><span>Outra subatividade — quero especificar</span></label></div>${state.subactivityId==='other'?`<div class="other-search">${field('otherSubactivity','Especifique a subatividade',{full:true,maxlength:300})}</div><small>Esta descrição precisa de confirmação de enquadramento. Não é uma categoria aprovada automaticamente.</small>`:''}<p class="sub-description">Revise a atividade e a subatividade escolhidas, mesmo quando vierem de uma sugestão.</p></div>`:'<p class="sub-description">A lista de subatividades aparece depois que você escolhe a atividade econômica.</p>';
  return form(`<div class="quote-form">${internal?baseFields(baseContext,state):'<p class="quote-helper">Conte sobre sua empresa. Vamos usar suas respostas para sugerir uma proteção.</p>'}<div id="cadastro-result" aria-live="polite"></div><section class="cnae-lookup">${field('cnae','Código da atividade econômica da empresa',{required:false,full:true,maxlength:10,help:'São os sete dígitos da classificação de atividade que constam no cadastro da empresa.'})}<button type="button" class="btn btn-outline" id="load-cnae-profile">Aproveitar referências desta atividade</button><div id="cnae-profile-status" role="status">${profileNotice()}</div></section><div id="activity-picker"></div>${sub}<div class="form-grid">${selectField('protection','O que você deseja proteger?',[['both','Imóvel e conteúdo'],['building','Somente o imóvel'],['contents','Somente o conteúdo']],{full:true})}${selectField('shopping','Sua empresa fica dentro de um shopping, prédio comercial ou galeria protegida?',[['yes','Shopping center'],['building','Prédio comercial'],['gallery','Galeria protegida'],['no','Nenhum desses locais']],{full:true})}</div><p class="catalog-note">${catalog.counts.activities} atividades do catálogo consultado em 28/10/2026. Os nomes foram escritos por extenso para facilitar a leitura. A escolha precisa refletir a atividade principal do negócio.</p></div>`);
}
function address(){return form(`<p class="quote-subtitle">${state.sourceKey?'Município da unidade identificado no cadastro. Se algum dado estiver ausente, complete apenas o necessário.':'Informe o endereço do local que você quer proteger.'}</p><div class="form-grid">${field('cep','CEP',{placeholder:'00000-000',maxlength:9,inputmode:'numeric',autocomplete:'postal-code',required:!state.sourceKey})}${field('number','Número',{maxlength:12,help:'Se não houver número, informe “sem número”.',required:!state.sourceKey})}${field('street','Endereço',{full:true,autocomplete:'address-line1',maxlength:200,required:!state.sourceKey})}${field('complement','Complemento',{full:true,required:false,autocomplete:'address-line2',maxlength:100})}${field('district','Bairro',{maxlength:100,required:!state.sourceKey})}${field('city','Cidade',{autocomplete:'address-level2',maxlength:100})}${selectField('uf','UF',['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'],{full:true})}</div><p class="catalog-note">O endereço é preenchido localmente. Na análise, a cidade e a UF localizam o município na API do IBGE. CEP e endereço completo não são enviados ao motor de recomendação nem à seguradora.</p>`,'Informar proteção');}
function protectionStep(){let fields=profileNotice()+productFields(state,selectField,productRules)+riskFields(state,questionnaire,field,{internal});if(!internal)fields=fields.replace('Campos sem confirmação preservam os sinais do cadastro. A triagem verifica condições do imóvel e o limite único básico de R$ 7,5 milhões.','Conte como é o imóvel e o que mais importa proteger. Se não souber uma resposta, deixe para confirmar.').replace('Estas confirmações opcionais ajudam a avaliar adicionais. Estimativas do cadastro não substituem sua resposta.','Estas perguntas ajudam a identificar proteções que podem fazer sentido para sua empresa.').replace('Pesos experimentais do MVP.','').replaceAll('Usar cadastro / a confirmar','Ainda não sei').replace('O foco escolhido multiplica por 1,5 os pesos das necessidades correspondentes. Não altera o risco territorial nem cria um preço.','Escolha o que mais importa para você. Isso ajuda a adaptar a sugestão às prioridades do seu negócio.').replace('Campos financeiros vazios aproveitam o cadastro vinculado; sem cadastro, ficam desconhecidos. Zero significa ausência confirmada.','Se não souber um valor, deixe em branco. Informe zero somente quando confirmar que não há esse item.').replace('Se vincular uma empresa, deixe vazio para usar o CNAE cadastrado. O código da lista de atividades não é um CNAE.','Se souber, informe o CNAE da sua empresa. Você pode deixar em branco.');return form(fields,'Calcular recomendação');}
function planStep(){if(!internal)return customerPlanStep();return form(`${internal?recommendationView(recommendation):customerRecommendationView(recommendation)}${voiceMarkup(state.sourceKey)}<p class="quote-subtitle plan-intro">Compare os pacotes padrão da política do guia: 6, 8 e 10 coberturas. A escolha manual e os ajustes serão recalculados antes de continuar.</p><div class="qplans">${plans.plans.map(p=>{const comparison=recommendation?.recomendacao.comparacao.find(c=>c.id===p.id);return `<label class="qplan ${p.id===recommendation?.planoId?'recommended-plan':''}">${p.id===recommendation?.planoId?'<span class="recommended-badge">Referência técnica recomendada</span>':''}<span class="qplan-top"><input type="radio" name="planId" value="${p.id}" ${p.id===state.planId?'checked':''} required><strong>${esc(p.name)}</strong></span><p>${p.assistances} assistências no snapshot público · ${comparison.coberturas.length} coberturas padrão no guia</p><p class="plan-fit"><strong>${comparison.aderencia_percentual.toFixed(1)}% de aderência</strong> · Meta ${comparison.meta_percentual}%</p>${comparison.coberturas_importantes_descobertas.length?`<p>Proteções prioritárias ausentes: ${comparison.coberturas_importantes_descobertas.map(c=>esc(recommendation.recomendacao.necessidades[c].nome)).join(', ')}</p>`:''}<details><summary>Ver coberturas padrão</summary><ul>${comparison.coberturas.map(c=>`<li>${esc(recommendation.recomendacao.necessidades[c].nome)}</li>`).join('')}</ul></details></label>`;}).join('')}</div>${packageFields(recommendation,state,productRules)}<p class="catalog-note">Valores comerciais do snapshot não representam preço deste pacote personalizado. Prêmio, franquias e aceitação dependem de cotação oficial.</p>`,'Continuar com este pacote');}
function customerPlanStep(){return form(`${customerRecommendationView(recommendation)}<h2>Escolha sua proteção</h2><div class="qplans">${plans.plans.map(p=>{const c=recommendation.recomendacao.comparacao.find(x=>x.id===p.id);return `<label class="qplan ${p.id===recommendation.planoId?'recommended-plan':''}"><span class="qplan-top"><input type="radio" name="planId" value="${p.id}" ${p.id===state.planId?'checked':''} required><strong>${esc(p.name)}</strong></span>${p.id===recommendation.planoId?'<p>Recomendado para suas respostas</p>':''}<p>${c.coberturas.length+recommendation.personalizacao.adicionais.filter(x=>x.solicitada&&x.plans.includes(c.plano)).length} coberturas no pacote para esta opção</p><details><summary>O que este plano inclui</summary><ul>${c.coberturas.map(k=>`<li>${esc(recommendation.recomendacao.necessidades[k].nome)}</li>`).join('')}${recommendation.personalizacao.adicionais.filter(x=>x.solicitada&&x.plans.includes(c.plano)).map(x=>`<li>${esc(fullName(x.name))}</li>`).join('')}</ul></details></label>`;}).join('')}</div>${optionalFields(recommendation,state)}<p class="catalog-note">A escolha será conferida pelo mesmo sistema antes de avançar. Preço, franquias e aceitação serão confirmados em uma cotação oficial.</p>`,'Continuar com este plano');}
async function applyPackage(){
  if(busy)return false;
  busy=true;
  const controls=$$('#quote-root button,#quote-form input,#quote-form select');
  controls.forEach(c=>{c.dataset.wasDisabled=String(c.disabled);c.disabled=true;});
  try{
    const before=recommendation?.personalizacao.pacote.aderencia_percentual;
    recommendation=await api('/api/recomendacao',{...riskPayload(state,questionnaire),...productPayload(state,productRules,true)});
    if(recommendation.recomendacao.indicacao_bloqueada){fail('A triagem exige análise oficial antes de prosseguir. Revise a situação do imóvel e o limite básico.');return false;}
    syncPackageState(recommendation,state,productRules);
    const after=recommendation.personalizacao.pacote.aderencia_percentual;
    render();if($('#package-status'))$('#package-status').textContent=`Ajustes aplicados. Aderência anterior ${before.toFixed(1)}%; atual ${after.toFixed(1)}%. ${packageCount(recommendation)} coberturas no seu pacote.`;
    return true;
  }catch(error){fail(error.message);return false;}
  finally{busy=false;controls.forEach(c=>{c.disabled=c.dataset.wasDisabled==='true';});}
}
function clearProfile(){
 clearTimeout(profileTimer);profileRevision++;profileLoading=false;for(const key of state.profileFields||[])state[key]='';state.profileFields=[];state.cnaeProfile=null;
}
function profileNotice(){
 const p=state.cnaeProfile;if(!p)return '';
 return `<aside class="prefill-notice"><strong>${p.amostra.empresas} empresas · Perfil de referência da atividade</strong><p>${esc(p.descricao)}</p><p>${esc(p.aviso)}</p>${Object.keys(p.valores).length?'<p>Os valores disponíveis já foram preenchidos. Você poderá revisá-los na etapa de proteção. As perguntas sobre condições reais do imóvel continuam necessárias.</p>':''}</aside>`;
}
async function requestProfile(){
 clearTimeout(profileTimer);
 const code=state.cnae.replace(/\D/g,'');if(code.length!==7){$('#cnae-profile-status').textContent='Informe os sete dígitos do código da atividade.';return;}
 const revision=++profileRevision;profileLoading=true;const status=$('#cnae-profile-status');status.textContent=internal?'Gerando relatório automático dos estabelecimentos deste CNAE…':'Consultando referências da atividade…';
 try{
  if(internal && !state.sourceKey){
    const report=await api('/api/interno/relatorio-cnae',{cnae:code});
    if(revision!==profileRevision||state.cnae.replace(/\D/g,'')!==code)return;
    cnaeReport=report;cadastroRecommendation=null;
    render();$('#quote-main').scrollIntoView({block:'start'});
    return;
   }
   const p=await api('/api/cnae/perfil',{cnae:code});if(revision!==profileRevision)return;
  const previousFields=new Set(state.profileFields||[]);state.cnaeProfile=p;state.profileFields=[];
  for(const [key,value] of Object.entries(p.valores)){if(!state.sourceKey&&(state[key]===''||state[key]==null||previousFields.has(key))){state[key]=String(value);state.profileFields.push(key);}}
  status.innerHTML=profileNotice();
 }catch(error){if(revision===profileRevision)status.textContent=error.message;}
 finally{if(revision===profileRevision)profileLoading=false;}
}
function resetUnitInputs(){
  clearProfile();state.prefilledFields=[];
  for(const k of ['contentsValue','equipmentValue','stockValue','buildingValue','glassValue','glassCount','employees','payroll','monthlyExpenses','monthlyRevenue','rentValue','units','securityControls','portableGoods','roofMaintained','exposedAssets','hasEmployees','hazardousWork','hasGlass','glassExposed'])state[k]='';
  initializeProductState(state,productRules);
}

function summary({includeContact=false}={}){
  const activity=selectedActivity(),sub=selectedSubactivity(),plan=selectedPlan();
  return `<div class="quote-review"><h2>Seu resumo</h2><dl>${includeContact?`<dt>${state.personType==='pj'?'Empresa':'Nome'}</dt><dd>${esc(state.name)}</dd><dt>Contato</dt><dd>${esc(state.email)}<br>${esc(state.phone)}</dd>`:''}<dt>Atividade</dt><dd>${esc(activity?.label||'Não selecionada')}</dd><dt>Subatividade</dt><dd>${esc(sub?.label||state.otherSubactivity||'A confirmar')}</dd><dt>Proteção</dt><dd>${esc({both:'Imóvel e conteúdo',building:'Somente o imóvel',contents:'Somente o conteúdo'}[state.protection]||'')}</dd><dt>Localização</dt><dd>${esc(state.city)} / ${esc(state.uf)}</dd><dt>Plano</dt><dd>${esc(plan?.name||'')}</dd><dt>Pacote calculado</dt><dd>${packageCount(recommendation)} coberturas · ${state.termYears} ${Number(state.termYears)===1?'ano':'anos'}</dd></dl></div>`;
}
function review(){return form(`${summary({includeContact:true})}<div class="form-grid">${selectField('payment','Como gostaria de pagar?',[['card','Cartão de crédito'],['debit','Débito em conta'],['boleto','Boleto bancário']],{full:true})}${selectField('installments','Quantidade de parcelas',[['1','À vista'],['2','2 parcelas'],['3','3 parcelas'],['4','4 parcelas'],['5','5 parcelas'],['6','6 parcelas'],['7','7 parcelas'],['8','8 parcelas'],['9','9 parcelas'],['10','10 parcelas'],['11','11 parcelas'],['12','12 parcelas']])}${selectField('paymentDay','Dia de vencimento',[['5','Dia 5'],['10','Dia 10'],['15','Dia 15'],['20','Dia 20'],['25','Dia 25']])}</div><p class="payment-note">Esta etapa demonstra a escolha de pagamento. Não solicita cartão, código de segurança ou dados bancários. Disponibilidade de parcelas, vencimentos e preço final precisam ser confirmados na contratação oficial.</p><label class="local-agreement"><input name="reviewed" type="checkbox" required ${state.reviewed?'checked':''}><span>Revisei as informações e quero concluir esta demonstração. Isso não contrata um seguro e não gera cobrança.</span></label>`,'Concluir demonstração');}
function success(){return `<div class="quote-success"><div class="success-icon" aria-hidden="true">✓</div><p>Você percorreu todas as etapas da demonstração. A recomendação foi calculada pelo motor local do MVP. Contatos e pagamento permanecem somente na memória da página; os dados de proteção são processados no servidor local, sem gravar proposta.</p>${summary()}<p>Para obter uma cotação válida e contratar, utilize o canal oficial da BB Seguros. Os dados preenchidos aqui não são transferidos.</p><button class="btn" id="download-summary">Baixar resumo sem dados pessoais</button><a class="btn btn-outline" href="https://cotacaoseguroempresarial.bbseguros.com.br/home" target="_blank" rel="noopener noreferrer">Abrir cotação oficial ↗</a><p><button class="back-button" id="restart-quote">Começar novamente e limpar os dados</button></p></div>`;}

function updateReportLayout(){
  const visible=step>=4||step===1&&Boolean(cadastroRecommendation||cnaeReport);
  document.body.classList.toggle('report-mode',visible);
  $('.quote-visual').hidden=visible;
}
function updateCadastroView(){
  updateReportLayout();
  const root=$('#cadastro-result');if(!root)return;
  root.setAttribute('aria-busy',String(cadastroLoading));
  root.innerHTML=cadastroLoading?'<p class="quote-helper" role="status">Analisando os dados do estabelecimento e comparando os planos…</p>':cadastroError?`<p class="quote-error" role="alert">${esc(cadastroError)}</p><button type="button" class="btn btn-outline" id="retry-cadastro">Tentar análise do cadastro novamente</button>`:cadastroRecommendation?(internal?cadastroRecommendationView(cadastroRecommendation)+voiceMarkup(state.sourceKey):'<div class="recommendation"><h2>Prévia do cadastro verificado</h2><p>Confira sua indicação inicial. Os dados ausentes ou estimados serão solicitados no formulário.</p>'+customerRecommendationView(cadastroRecommendation)+'</div>'):'';
  if(internal&&cadastroRecommendation)bindVoice(state.sourceKey);
  $('#retry-cadastro')?.addEventListener('click',requestCadastro);
}
async function requestCadastro(){
  const revision=++cadastroRevision,sourceKey=state.sourceKey;
  cadastroRecommendation=null;cadastroError='';cadastroLoading=Boolean(sourceKey);updateCadastroView();
  if(!sourceKey)return;
  const [empresaId,imovelId]=sourceKey.split('|');
  try{
    const result=await api('/api/recomendacao/cadastro',{empresaId,imovelId});
    if(revision!==cadastroRevision||sourceKey!==state.sourceKey)return;
    cadastroRecommendation=result;
    if(result.preenchimento){state.profileFields=[];state.cnaeProfile=null;state.prefilledFields=Object.keys(result.preenchimento);for(const [key,value] of Object.entries(result.confirmacoesDisponiveis||{})){state[key]=value;state.prefilledFields.push(key);}for(const [k,v] of Object.entries(result.preenchimento))if(state[k]===''||state[k]==null)state[k]=String(v);syncEmployeeExposure(state,null);state.cnae=result.atividade.cnaeUtilizado||state.cnae;const input=$('#cnae');if(input)input.value=state.cnae;}
  }catch(error){
    if(revision!==cadastroRevision||sourceKey!==state.sourceKey)return;
    cadastroError=error.message;
  }finally{
    if(revision===cadastroRevision){cadastroLoading=false;updateCadastroView();}
  }
}
async function verifyClient(){
 const code=$('#client-access-code')?.value||'',cnpj=state.cnpj,button=$('#verify-client'),status=$('#client-status');
 if(!validCnpj(cnpj)){status.textContent='Confira o CNPJ da empresa.';return;}
 if(code.length<8){status.textContent='Informe seu código de verificação.';return;}
 button.disabled=true;status.textContent='Verificando o vínculo empresarial…';
 try{
   await api('/api/cliente/vincular',{cnpj,code});
   const result=await api('/api/cliente/cadastro',{});
   const e=result.cadastro||{};
   if(!e.empresa_id||!e.imovel_id)throw new Error('Cadastro vinculado sem estabelecimento.');
   state.sourceKey=e.empresa_id+'|'+e.imovel_id;
   state.city=result.localizacao?.municipio_real||'';
   state.uf=result.localizacao?.uf_real||'';
   state.cnae=result.atividade?.cnaeUtilizado||'';
   cadastroRecommendation=result;cadastroError='';cadastroLoading=false;
   state.prefilledFields=Object.keys(result.preenchimento||{});state.profileFields=[];state.cnaeProfile=null;
   for(const [k,v] of Object.entries(result.preenchimento||{}))if(state[k]===''||state[k]==null)state[k]=String(v);
   for(const [k,v] of Object.entries(result.confirmacoesDisponiveis||{})){state[k]=v;state.prefilledFields.push(k);}
   const groupMapping={RESTAURANTE:'625',FARMACIA:'476',MERCADO:'909',VAREJO_MODA:'484',CLINICA:'690',BELEZA:'641',ESCOLA_CURSO:'728',ESCRITORIO:'674',ELETRONICOS:'1007'};
   const inferred=groupMapping[e.grupo_atividade];
   if(inferred&&catalog.activities.some(a=>a.id===inferred)){
     state.activityId=inferred;
     const activity=catalog.activities.find(a=>a.id===inferred);
     if(activity.subactivities.length===1)state.subactivityId=activity.subactivities[0].id;
   }
   // Nunca converter ausencia de confirmação em respostas "Não".
   const answered=questionnaire.groups.flatMap(g=>g.questions.map(q=>q.id)).filter(k=>k!=='hasEmployees')
     .every(k=>state[k]==='yes'||state[k]==='no');
   const complete=!!(state.activityId&&state.subactivityId&&state.protection&&state.shopping&&state.city&&state.uf&&answered);
   if(complete){
     const report=await api('/api/recomendacao',{...riskPayload(state,questionnaire),...productPayload(state,productRules)});
     recommendation=report;syncPackageState(report,state,productRules);completed=4;step=4;
   }else{completed=Math.max(completed,1);step=1;}
   history.replaceState({quoteStep:step},'',journeyPath+'?etapa='+(step+1));
   render();
   if(!complete){const target=$('#cadastro-result');if(target)target.scrollIntoView({block:'start'});}
 }catch(e){status.textContent=e.message;button.disabled=false;}
}
function invalidate(){recommendation=null;state.planId='';state.reviewed=false;completed=Math.min(completed,3);$$('[data-step]').forEach(b=>{b.disabled=Number(b.dataset.step)>completed;});}
function remember(e){const t=e.target;if(!t.name||!(t.name in state))return;if(t.name.startsWith('extra_'))state['excludeExtra_'+t.name.slice(6)]=!t.checked;if(Array.isArray(state.profileFields)&&state.profileFields.includes(t.name))state.profileFields=state.profileFields.filter(k=>k!==t.name);if(t.name==='cnae'&&e.type==='input'){clearProfile();cnaeReport=null;}const previousEmployees=state.employees;state[t.name]=t.type==='checkbox'?t.checked:t.value;if(t.name==='cnae'&&e.type==='input'&&state.cnae.replace(/\D/g,'').length===7)profileTimer=setTimeout(requestProfile,350);if(t.name==='employees'&&employeePresence(state)===false){state.payroll='0';const payrollInput=$('#payroll');if(payrollInput)payrollInput.value='0';state.profileFields=(state.profileFields||[]).filter(k=>k!=='payroll');}if(t.name==='employees'){const presence=syncEmployeeExposure(state,previousEmployees);$$('[data-employee-exposure] input').forEach(r=>{r.disabled=presence===false;r.required=presence!==false;r.checked=r.value===state.hazardousWork;});}if(t.name==='shopping'&&t.value!=='yes')state.op_shoppingControls='';if(step===4){if(t.name.startsWith('op_')||t.name==='planId'){for(const x of productRules.optional){const plan={892:'ESSENCIAL',893:'PRATICO',894:'TOTAL'}[state.planId];if(state['op_'+x.operation]!=='yes'||!x.plans.includes(plan))state['extra_'+x.code]=false;else if(x.operation!=='interruption'&&!state['excludeExtra_'+x.code])state['extra_'+x.code]=true;}if(e.type==='change')render();}if(t.name.startsWith('extra_LUCRO_')&&t.checked){for(const x of productRules.optional.filter(x=>x.code.startsWith('LUCRO_'))){if('extra_'+x.code!==t.name){state['extra_'+x.code]=false;state['excludeExtra_'+x.code]=true;}}if(e.type==='change')render();}const status=$('#package-status');if(status)status.textContent='Há alterações pendentes. Aplique os ajustes para atualizar o pacote.';return;}if(!['name','cnpj','birthDate','maritalStatus','phone','email','personType','planId','payment','installments','paymentDay','reviewed','description'].includes(t.name))invalidate();if(t.name==='phone'){let v=t.value.replace(/\D/g,'').slice(0,11);if(v.length>2)v=`(${v.slice(0,2)}) ${v.slice(2)}`;if(v.replace(/\D/g,'').length>7)v=v.slice(0,-4)+'-'+v.slice(-4);t.value=v;state.phone=v;}if(t.name==='cep'){const v=t.value.replace(/\D/g,'').slice(0,8);t.value=v.length>5?v.slice(0,5)+'-'+v.slice(5):v;state.cep=t.value;}}
function fail(message){$('#form-errors').innerHTML=`<p class="quote-error">${esc(message)}</p>`;$('#form-errors').scrollIntoView({block:'nearest'});return false;}
function validCnpj(value){const digits=value.replace(/\D/g,'');if(digits.length!==14||/^(\d)\1+$/.test(digits))return false;function digit(base){let weight=base.length-7;let sum=0;for(const c of base){sum+=Number(c)*weight--;if(weight===1)weight=9;}const rest=sum%11;return rest<2?'0':String(11-rest);}return digit(digits.slice(0,12))===digits[12]&&digit(digits.slice(0,13))===digits[13];}
function validateStep(){
  if(step===0){if(state.name.trim().length<3)return fail('Informe o nome ou razão social com pelo menos três caracteres.');if(state.personType==='pj'&&!validCnpj(state.cnpj))return fail('Confira o CNPJ da empresa.');if(![10,11].includes(state.phone.replace(/\D/g,'').length))return fail('Informe um telefone com DDD e número completo.');}
  if(step===1){if(!selectedActivity())return fail('Escolha uma atividade na lista ou confirme uma sugestão da busca inteligente.');if(state.subactivityId==='other'){if(state.otherSubactivity.trim().length<4)return fail('Descreva a outra subatividade para revisão.');}else if(!isValidSelection(catalog,state.activityId,state.subactivityId))return fail('Escolha uma subatividade vinculada à atividade selecionada.');}
  if(step===2&&!state.sourceKey&&state.cep.replace(/\D/g,'').length!==8)return fail('Confira o CEP com oito números.');
  if(step===3){const presence=employeePresence(state);state.hasEmployees=presence===null?'':presence?'yes':'no';if(state.glassCount!==''&&(!Number.isInteger(Number(state.glassCount))||Number(state.glassCount)<0||Number(state.glassCount)>1000000))return fail('Informe uma quantidade inteira de itens de vidro ou deixe em branco.');if(state.glassCount!==''&&((Number(state.glassCount)===0&&state.hasGlass==='yes')||(Number(state.glassCount)>0&&state.hasGlass==='no')))return fail('A quantidade de itens de vidro não combina com a resposta sobre ter vidros para proteger. Revise as duas informações.');if(questionnaire.groups.some(g=>g.questions.some(q=>q.id!=='hasEmployees'&&!['yes','no'].includes(state[q.id]))))return fail('Responda às perguntas sobre a proteção. A quantidade de empregados pode ficar em branco se não souber.');if(state.hasEmployees==='no'&&state.hazardousWork==='yes')return fail('Sem empregados, responda Não à exposição dos empregados.');if(state.hasGlass==='no'&&state.glassExposed==='yes')return fail('Sem vidros, responda Não à exposição dos vidros.');}
  if(step===4&&!selectedPlan())return fail('Escolha um plano para continuar.');
  return true;
}
function go(value,{historyEntry=true}={}){if(busy||value<0||value>Math.min(completed,6))return;if(value>=4&&!recommendation){value=3;completed=Math.min(completed,3);}step=value;render();if(historyEntry)history.pushState({quoteStep:step},'',`${journeyPath}?etapa=${step+1}`);$('#quote-main').scrollIntoView({block:'start'});$('#quote-main').focus({preventScroll:true});}
function downloadSummary(){const a=selectedActivity(),s=selectedSubactivity();const result=internal?{demonstracao:true,contratacao:false,atividade:{codigo:a.id,nome:a.label},subatividade:s?{codigo:s.id,nome:s.label}:{codigo:null,nome:state.otherSubactivity,confirmacaoPendente:true},protecao:state.protection,plano:selectedPlan()?.name,pagamentoPreferido:state.payment,analise:recommendation?{versao:recommendation.versao,vidrosDeclarados:recommendation.vidrosDeclarados,indices:recommendation.indices,recomendacao:recommendation.recomendacao,rastreabilidade:recommendation.rastreabilidade,personalizacao:recommendation.personalizacao,dimensionamento:recommendation.dimensionamento,patrimonio:recommendation.patrimonio,fontes:recommendation.fontes,avisos:recommendation.avisos,respostas:recommendation.respostas}:null,observacao:'Não é cotação oficial. Inclui os dados empresariais usados no cálculo. Sem contatos, documentos pessoais, dados de pagamento, endereço completo ou descrição livre.'}:customerReport(recommendation);const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='resumo-demonstracao-empresarial.json';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
document.addEventListener('pointerdown',e=>{if(picker?.open&&!picker.root.contains(e.target))picker.setOpen(false);});
window.addEventListener('popstate',e=>{const target=e.state?.quoteStep??0;go(Math.min(target,completed),{historyEntry:false});});

try{
  const responses=await Promise.all([fetch('/activities.json'),fetch('/plans.json'),fetch('/questionnaire.json'),fetch('/product-rules.json')]);
  if(responses.some(r=>!r.ok))throw new Error('Falha ao carregar o catálogo.');
  [catalog,plans,questionnaire,productRules]=await Promise.all(responses.map(r=>r.json()));
  initializeProductState(state,productRules);
  index=createActivityIndex(catalog);
  if(!plans.plans.some(p=>p.id===state.planId))state.planId='';
  history.replaceState({quoteStep:step},'',journeyPath);
  document.body.classList.toggle('internal-journey',internal);
  $('.quote-header').innerHTML=internal?'<a class="brand" href="/interno">BB Seguros · Consultoria</a><span>Prospecção ativa · Ambiente local de demonstração</span>':'<a class="brand" href="/">BB Seguros</a><a href="/seguros/seguro-empresarial">← Conheça o seguro</a>';
  if(internal){TITLES[1]='Painel de prospecção ativa';LABELS[0]='Contato';$('.quote-visual-content').innerHTML='<p>Inteligência para sua consultoria</p><h2>Dados que apoiam boas conversas.</h2><span>Selecione uma empresa, confira os dados e fundamente sua recomendação.</span>';}
  render();
}catch(error){$('#quote-root').innerHTML=`<div class="quote-load-error" role="alert"><h1>Não foi possível abrir o formulário.</h1><p>${esc(error.message)}</p><button class="btn" id="retry-catalog">Tentar novamente</button></div>`;$('#retry-catalog').addEventListener('click',()=>location.reload());}
