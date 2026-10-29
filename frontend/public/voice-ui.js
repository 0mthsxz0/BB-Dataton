import { api } from './quote-engine.js';
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function voiceMarkup(sourceKey){
 if(!sourceKey)return '';
 return '<section class="voice-panel" id="voice-panel" aria-label="Ligação personalizada do relatório">'+
 '<p class="result-eyebrow">Prospecção ativa · Voz por IA</p><h2>Ligar a partir deste relatório</h2>'+
 '<p>O sistema cria um roteiro preliminar usando apenas os dados deste estabelecimento. Revise e aprove antes de solicitar uma ligação. O envio real está desligado até a configuração da Twilio.</p>'+
 '<div class="voice-grid"><label>Nome comercial confirmado<input id="voice-enterprise" maxlength="100" placeholder="Nome informado pelo colaborador"></label>'+
 '<label>Nome do contato (opcional)<input id="voice-contact" maxlength="60"></label>'+
 '<label>Colaborador (opcional)<input id="voice-employee" maxlength="60"></label>'+
 '<label>Organização<input id="voice-organization" maxlength="60" value="Equipe de seguros"></label></div>'+
 '<button class="btn btn-outline" type="button" id="voice-generate">Gerar roteiro do relatório</button>'+
 '<div id="voice-editor" hidden><p id="voice-origin" class="catalog-note"></p><label for="voice-text"><strong>Mensagem que será falada</strong></label>'+
 '<textarea id="voice-text" rows="8" maxlength="1500"></textarea><p class="catalog-note">O roteiro é um rascunho. Revise as condições, não prometa preço, aprovação ou cobertura automática.</p>'+
 '<button class="btn btn-outline" type="button" id="voice-approve">Aprovar este texto</button>'+
 '<div class="voice-call" hidden id="voice-call"><label for="voice-phone">Telefone internacional do destinatário</label><input id="voice-phone" type="tel" autocomplete="off" placeholder="+5561999999999">'+
 '<label class="voice-check"><input type="checkbox" id="voice-authorized"> Confirmei que o contato pode receber esta ligação comercial.</label>'+
 '<label class="voice-check"><input type="checkbox" id="voice-confirmed"> Li e aprovei o roteiro e quero iniciar esta única chamada.</label>'+
 '<button class="btn" type="button" id="voice-send">Ligar agora</button></div></div><p id="voice-status" role="status"></p></section>';
}
export function bindVoice(sourceKey, payloadBuilder) {
 const root=document.getElementById('voice-panel');if(!root||!sourceKey)return;
 const [empresaId,imovelId]=sourceKey.split('|');let draft=null,approval=null;
 const status=(m,error=false)=>{const e=root.querySelector('#voice-status');e.textContent=m;e.classList.toggle('quote-error',error);};
 const q=x=>root.querySelector(x);
 const reset=()=>{approval=null;q('#voice-call').hidden=true;};
 q('#voice-generate').addEventListener('click',async()=>{
   reset();const button=q('#voice-generate');button.disabled=true;
   try{
    status('Preparando roteiro a partir da recomendação calculada…');
    const data={empresaId,imovelId,empresa:q('#voice-enterprise').value,contato:q('#voice-contact').value,colaborador:q('#voice-employee').value,organizacao:q('#voice-organization').value};
    if(payloadBuilder){const calculated=payloadBuilder();if(calculated)data.cotacaoPayload=calculated;}
    draft=await api('/api/interno/roteiros',data);
    q('#voice-text').value=draft.text;q('#voice-editor').hidden=false;
    q('#voice-origin').textContent=draft.origin==='ia-rascunho'?'Rascunho gerado por IA. Conferir dados e justificativas.':'Roteiro seguro gerado pelas regras do relatório (sem IA externa, ou fallback).';
    status('Roteiro pronto para revisão.');
   }catch(e){status(e.message,true);}finally{button.disabled=false;}
 });
 q('#voice-text').addEventListener('input',reset);
 q('#voice-approve').addEventListener('click',async()=>{
   if(!draft)return;const btn=q('#voice-approve');btn.disabled=true;
   try{approval=await api('/api/interno/roteiros/aprovar',{id:draft.id,text:q('#voice-text').value});q('#voice-call').hidden=false;status('Texto aprovado. Revise o telefone e autorize o contato para habilitar a ligação.');}
   catch(e){status(e.message,true);}finally{btn.disabled=false;}
 });
 q('#voice-send').addEventListener('click',async()=>{
   if(!approval)return;const btn=q('#voice-send');btn.disabled=true;
   try{const result=await api('/api/interno/ligacoes',{id:draft.id,approvalHash:approval.approvalHash,phone:q('#voice-phone').value.trim(),authorizedContact:q('#voice-authorized').checked,confirmed:q('#voice-confirmed').checked});status('Solicitação registrada pela Twilio. Estado inicial: '+(result.call?.status||'a consultar')+'.');}
   catch(e){status(e.message,true);}
   finally{btn.disabled=false;}
 });
}
