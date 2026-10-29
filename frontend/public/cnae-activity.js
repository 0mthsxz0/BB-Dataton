/** Associa CNAE à atividade do catálogo de seguros, sem usar perfil financeiro de terceiros. */
import { isValidSelection, searchActivities } from './activity-search.js';

/*
 * Equivalências conferidas por atividade + subatividade.
 * Um código CNAE não é um código do catálogo de seguros; nunca usar IDs numéricos
 * intercambiavelmente nem inventar subatividade na ausência de equivalência.
 */
const DE_PARA = Object.freeze({
  '4771701': {activityId:'476',subactivityId:'F2.20'}
});

export function classificarCnae(resposta,catalog,index){
 const cnae=String(resposta?.cnae||'').replace(/\D/g,'');
 const descricao=String(resposta?.descricao||'').trim();
 if(!/^\d{7}$/.test(cnae)||!resposta?.encontrado||!descricao)
   return {tipo:'nao_encontrado',descricao:'',cnae,sugestoes:[]};
 const direto=DE_PARA[cnae];
 if(direto && isValidSelection(catalog,direto.activityId,direto.subactivityId)){
   return {tipo:'automatico',cnae,descricao,...direto,origem:'equivalencia_validada',sugestoes:[]};
 }
 const busca=searchActivities(index,descricao,{mode:'description',limit:3});
 const [primeiro,segundo]=busca.results;
 const margem=(primeiro?.score||0)-(segundo?.score||0);
 const sugestoes=busca.results.map(item=>({
   activityId:item.activity.id,atividade:item.activity.label,
   subactivityId:item.subactivity?.id||null,subatividade:item.subactivity?.label||null
 }));
 // Só avançar quando a busca tem confiança forte, margem alta e
 // subatividade efetivamente pertencente à mesma categoria do catálogo.
 if(busca.confidence==='strong'&&margem>=12&&primeiro?.subactivity
    &&!primeiro.requiresSubactivityConfirmation
    &&isValidSelection(catalog,primeiro.activity.id,primeiro.subactivity.id)){
   return {tipo:'automatico',cnae,descricao,activityId:primeiro.activity.id,
     subactivityId:primeiro.subactivity.id,origem:'descricao_compativel',sugestoes};
 }
 return {tipo:'confirmar',cnae,descricao,sugestoes};
}
