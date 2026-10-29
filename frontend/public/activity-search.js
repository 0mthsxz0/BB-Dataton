import { ALIASES, REFINEMENTS, VOCABULARY_VERSION, CONCEPTS } from './activity-vocabulary.js';
/** Offline relevance search over insurer-owned categories; no insurance decisions. */
export function normalize(text) {
  return String(text ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR').replace(/[^a-z0-9]+/g,' ').trim();
}
const STOP = new Set('a o as os de da do das dos e ou um uma uns umas em na no nas nos meu minha meus minhas seu sua seus suas eu nos voce voces tenho temos empresa negocio trabalhar trabalho funciona fazemos faco que com para pelo pela pelos pelas por aqui la muito mais tambem somente apenas sao ser sendo esta este essa esses estas esse isto isso nosso nossa nossos nossas precisa quero gostaria'.split(' '));
function root(word) {
  if(word.length>5&&word.endsWith('oes'))return word.slice(0,-3)+'ao';
  if(word.length>4&&word.endsWith('ais'))return word.slice(0,-3)+'al';
  if(word.length>4&&word.endsWith('s'))return word.slice(0,-1);
  return word;
}
export function tokens(text){return normalize(text).split(' ').filter(w=>w.length>1&&!STOP.has(w)).map(root);}


export function createActivityIndex(catalog) {
  const entries=catalog.activities.map(activity=>{
    const text=activity.label;
    const ts=tokens(text);
    return {activity,normalized:normalize(text),tokens:ts,bag:new Set(ts),
      subTokens:new Set(activity.subactivities.flatMap(s=>tokens(s.label)))};
  });
  const frequency=new Map();
  for(const row of entries)for(const word of row.bag)frequency.set(word,(frequency.get(word)||0)+1);
  return {entries,frequency,size:entries.length};
}

function grams(text){const t=' '+normalize(text)+' ';const g=new Set();for(let i=0;i<t.length-2;i++)g.add(t.slice(i,i+3));return g;}
function similarity(a,b){const aa=grams(a),bb=grams(b);let n=0;for(const g of aa)if(bb.has(g))n++;return 2*n/(aa.size+bb.size||1);}
function idf(index,word){return Math.log(1+(index.size+1)/((index.frequency.get(word)||0)+1));}
// Keep clause boundaries until negative assertions have been removed.
export function positiveDescription(text) {
  return String(text).split(/[,;.!?\n]+|\bmas\b|\bporem\b|\be sim\b|\be\s+(?=(?:vendo|vendemos|fabrico|fabricamos|produzo|produzimos|conserto|reparo|presto)\b)/iu)
    .map(clause=>normalize(clause).replace(/\b(?:nao|nunca|nem)\b.*$/g,''))
    .filter(Boolean).join(' ');
}
function negatedText(text){return positiveDescription(text);}
function interpreted(text){let value=positiveDescription(text);for(const [pattern,replacement] of ALIASES)value=value.replace(pattern,replacement);return value;}
function operation(text){
  const cleaned=negatedText(normalize(text));
  if(/\b(conserto|consertamos|reparo|reparamos|manutencao|assistencia tecnica)\b/.test(cleaned))return 'repair';
  if(/\b(fabrico|fabricamos|produzo|produzimos|fabricacao|fabrica|industria)\b/.test(cleaned))return 'manufacture';
  if(/\b(atacado|atacadista|distribuidora|distribuimos)\b/.test(cleaned))return 'wholesale';
  if(/\b(vendo|vende|vendem|venda|vendemos|revendo|revendemos|loja|varejo|varejista|comercializo|comercializamos|comercio)\b/.test(cleaned))return 'retail';
  return null;
}
const GENERIC_INTENT = new Set('vendo vende vendem venda vendemos revendo revendemos loja lojas varejo varejista atacado atacadista comercio comercializo comercializamos fabrico fabricamos produzo produzimos fabricacao fabrica industria conserto consertamos reparo reparamos manutencao reparacao assistencia tecnica presto prestamo servico servicos produto produtos consumidor consumidore cliente cliente principal atividade pessoa coisa diverso diversa geral'.split(' ').map(root));
function candidateOperation(label){if(label.startsWith('fabricacao')||label.startsWith('confeccao'))return 'manufacture';if(label.includes('atacadista'))return 'wholesale';if(label.includes('varejista'))return 'retail';if(/reparacao|manutencao/.test(label))return 'repair';if(label.startsWith('servicos'))return 'service';return null;}

// A place of work ("prédio comercial") does not identify a consulting specialty.
function consultancyIntent(text) {
  if(!/\b(consultoria\w*|consultor|consultores|consultora\w*|assessoria\w*)\b/.test(text))return null;
  if(/\b(gestao|administrativa)\b/.test(text))return {ids:['721'],reason:'consultoria de gestão administrativa'};
  if(/\b(software|programa\w*|sistemas?|aplicativo\w*)\b/.test(text))return {ids:['1008'],reason:'consultoria em programas de computador'};
  if(/\b(informatica|hardware|computador\w*|equipamentos? de informatica)\b/.test(text))return {ids:['1005'],reason:'consultoria em equipamentos de informática'};
  if(/\b(engenhari\w*|arquitet\w*|tecnica especializada)\b/.test(text))return {ids:['669'],reason:'assessoria técnica de engenharia ou arquitetura'};
  if(/\b(decoracao|interiores)\b/.test(text))return {ids:['672'],reason:'consultoria e projetos de decoração'};
  if(/\b(financeir\w*|contab\w*|tributari\w*|juridic\w*)\b/.test(text))return {ids:['674'],reason:'assessoria financeira, contábil ou jurídica'};
  return {ids:['721','674'],reason:'consultoria ou assessoria para empresas',question:'Sua consultoria é de gestão/administrativa, financeira/contábil, tecnologia ou engenharia? Conte o serviço principal para refinar estas possibilidades do catálogo.'};
}

/** Returns only identifiers belonging to the supplied parent/subactivity catalog. */
export function searchActivities(index, query, {mode='name',limit=12,refinements={}}={}) {
  const original=query;
  query=mode==='description'?interpreted(query):query;
  const refinementText=Object.entries(refinements).map(([key,value])=>REFINEMENTS[key]?.[value]||'').join('. ');
  if(mode==='description'&&refinementText)query+=' '+interpreted(refinementText);
  const q=normalize(query);
  if(!q)return {results:mode==='name'?index.entries.slice(0,limit).map(x=>({activity:x.activity,score:0,reason:'Lista de atividades'})):[],confidence:'none',question:mode==='description'?'Conte o que você vende, produz ou faz e quem são seus clientes.':null};
  // Ignore negated operations/products before ranking, not just when detecting intent.
  let rawTokens=tokens(mode==='description'?negatedText(q):query);
  if(mode==='description')rawTokens=rawTokens.map(token=>{
    if(token.length<5||index.frequency.has(token))return token;
    const candidates=[...index.frequency.keys()].filter(w=>Math.abs(w.length-token.length)<=1&&w[0]===token[0]&&similarity(token,w)>.73);
    return candidates.length===1?candidates[0]:token;
  });
  if(mode==='description'&&rawTokens.length<1)return {results:[],confidence:'none',question:'Conte o que você vende, produz ou faz e quem são seus clientes.'};
  const clean=negatedText(q);
  const consultancy=mode==='description'?consultancyIntent(clean):null;
  const concepts=mode==='description'?CONCEPTS.filter(c=>c.pattern.test(clean)):[];
  const additions=concepts.flatMap(c=>tokens(c.terms));
  const qtokens=[...new Set([...rawTokens,...additions])];
  const op=refinements.operation||operation(query);
  const productTokens=rawTokens.filter(t=>!GENERIC_INTENT.has(t));
  const wholeVehicle=/\b(veiculos?|automoveis)\b/.test(clean)&&!/\b(pecas?|acessorios?|pneumaticos?|ferroviari\w*|biciclet\w*|motociclet\w*)\b/.test(clean);
  const vehicleRental=wholeVehicle&&/\b(alugo|aluguel|locacao|arrendamento)\b/.test(clean);
  const vehicleWash=wholeVehicle&&/\b(lavo|lavamos|lavagem|lava rapido|lava jato|lubrificacao)\b/.test(clean);
  const vehicleSales=wholeVehicle&&!vehicleRental&&!vehicleWash&&(!op||op==='retail');
  const vehicleIds=wholeVehicle?(vehicleRental?['697','954']:vehicleWash?['683']:op==='repair'?['633']:op==='manufacture'?['821']:vehicleSales?(refinements.vehicleBusiness==='dealer'||/\bconcessionaria\w*\b/.test(clean)?['905']:refinements.vehicleBusiness==='agency'||/\b(agencia|revenda independente)\b/.test(clean)?['906']:['905','906']):[]):null;
  const medicine=/\b(medicament\w*|farmaci\w*|drogari\w*)\b/.test(clean);
  const animal=refinements.audience?refinements.audience==='animal':/\b(animais|animal|veterin\w*|pets?|cachorros?|gatos?)\b/.test(clean);
  const cosmetics=/\b(cosmetic\w*|perfum\w*)\b/.test(clean)&&!medicine;
  const cosmeticId=op==='manufacture'?'288':op==='wholesale'?'554':'477';
  const medicineIds=medicine?(op==='manufacture'?[animal?'292':'291']:op==='wholesale'?[animal?'555':'553']:[animal?'478':'476']):[];
  const ranked=[];
  for(const row of index.entries){
    if(consultancy&&!consultancy.ids.includes(row.activity.id))continue;
    if(vehicleIds&&!vehicleIds.includes(row.activity.id))continue;
    let score=consultancy?24:0;
    if(vehicleIds?.includes(row.activity.id))score+=24;
    if(cosmetics)score+=row.activity.id===cosmeticId?28:-22;
    if(medicine&&medicineIds.includes(row.activity.id))score+=28;
    if(medicine&&!medicineIds.includes(row.activity.id))score-=22;const matches=[];
    for(const token of qtokens){
      const exact=row.bag.has(token);
      const prefix=!exact&&token.length>=4&&[...row.bag].some(w=>w.startsWith(token)||token.startsWith(w)&&w.length>=4);
      if(exact||prefix){score+=idf(index,token)*(exact?1:.65)*(rawTokens.includes(token)?1:.65);matches.push(token);}
      else if(row.subTokens.has(token)){score+=idf(index,token)*.55;matches.push(token);}
    }
    if(row.normalized.includes(q))score+=15;
    if(row.activity.id===query.trim())score+=40;
    if(row.activity.subactivities.some(s=>normalize(s.id)===q))score+=35;
    for(const concept of concepts){if(concept.ids?.includes(row.activity.id))score+=17;}
    if(/roupas?|vestuario|brecho|boutique|moda/.test(clean)){
      if(op==='retail'&&row.activity.id==='484')score+=24;
      if(op==='wholesale'&&row.activity.id==='562')score+=24;
      if(op==='manufacture'&&row.activity.id==='855')score+=20;
    }
    if(/moveis|marcenar|mobiliario|armario/.test(clean)){
      if(op==='manufacture'&&row.activity.id==='226'&&/madeira|marcenar/.test(clean))score+=25;
      if(op==='retail'&&row.activity.id==='489')score+=24;
      if(op==='wholesale'&&row.activity.id==='567')score+=24;
    }
    const productMatches=productTokens.filter(t=>row.bag.has(t));
    if(mode==='description'&&!consultancy&&!medicine&&!cosmetics&&!vehicleIds&&!matches.length&&!concepts.some(c=>c.ids?.includes(row.activity.id)))continue;
    const cop=candidateOperation(row.normalized);
    if(op&&cop)score+=op===cop?8:-18;
    // Common-language descriptions disambiguate software product vs custom work.
    if(row.activity.id==='1008'&&/sob encomenda|sob medida|para clientes/.test(q))score+=15;
    if(row.activity.id==='1006'&&/produto proprio|licenc|comercializ/.test(q))score+=15;
    if(row.activity.id==='1007'&&op==='repair'&&/computador|notebook|informatica|celular|smartphone/.test(q))score+=22;
    if(mode==='name'&&score<3&&qtokens.length<=3){const fuzzy=Math.max(...qtokens.map(t=>Math.max(0,...row.tokens.map(w=>similarity(t,w)))));if(fuzzy>.62)score+=fuzzy*5;}
    if(score<=0)continue;
    const subCandidates=row.activity.subactivities.map(s=>{
      const st=new Set(tokens(s.label));let subScore=0;for(const t of qtokens){if(st.has(t))subScore+=idf(index,t);else if(t.length>=5&&[...st].some(w=>w.length>=5&&similarity(t,w)>.72))subScore+=idf(index,t)*.5;}
      if(normalize(s.label).includes(q))subScore+=10;
      if(normalize(s.id)===q)subScore+=40;
      return {subactivity:s,score:subScore};
    }).sort((a,b)=>b.score-a.score||a.subactivity.label.localeCompare(b.subactivity.label,'pt-BR'));
    let sub= subCandidates.length===1 ? subCandidates[0].subactivity : subCandidates[0]?.score>0&&(subCandidates[0].score-(subCandidates[1]?.score||0))>=2 ? subCandidates[0].subactivity : null;
    const requiresSubactivityConfirmation=Boolean(sub&&/terreo|sobrado/.test(normalize(sub.label))&&!/\b(terreo|sobrado)\b/.test(clean));
    if(requiresSubactivityConfirmation)sub=null;
    const reason=(vehicleIds?.includes(row.activity.id)?`Você descreveu ${vehicleRental?'locação':vehicleWash?'lavagem':op==='repair'?'reparação':op==='manufacture'?'fabricação':'venda'} de veículos; confira o tipo de estabelecimento`:null)||(medicineIds.includes(row.activity.id)?`Você informou ${animal?'medicamentos para animais':'medicamentos ou farmácia'}; esta opção corresponde a ${op==='manufacture'?'fabricação':op==='wholesale'?'venda no atacado':'venda ao consumidor'}`:null)||consultancy?.reason||concepts.filter(c=>c.ids?.includes(row.activity.id)).map(c=>c.reason).join('; ')|| (matches.length?`Termos relacionados: ${[...new Set(matches)].slice(0,4).join(', ')}`:'Nome aproximado');
    ranked.push({productMatches,activity:row.activity,subactivity:sub,score,reason,requiresSubactivityConfirmation,subactivityReason:subCandidates.length===1?'Única subatividade vinculada a esta atividade no catálogo':sub?'Descrição compatível com a subatividade':'Escolha a subatividade para confirmar'});
  }
  if(mode==='description'&&!consultancy&&!concepts.length&&!medicine&&!cosmetics&&!vehicleIds&&ranked.some(r=>r.productMatches.length)){for(let i=ranked.length-1;i>=0;i--)if(!ranked[i].productMatches.length)ranked.splice(i,1);}
  ranked.sort((a,b)=>b.score-a.score||a.activity.label.localeCompare(b.activity.label,'pt-BR'));
  const top=ranked[0],margin=top?(top.score-(ranked[1]?.score||0)):0;
  const sufficient=mode==='name'||(top&&top.score>=12&&(consultancy||concepts.length>0||medicine||cosmetics||vehicleIds||top.productMatches.some(t=>idf(index,t)>=2.5)||productTokens.filter(t=>tokens(top.activity.label+' '+(top.subactivity?.label||'')).includes(t)).length>=2));
  const results=sufficient?(mode==='description'?ranked.filter(r=>r.score>=Math.max(8,(top?.score||0)*.4)):ranked).slice(0,limit):[];
  let confidence=!results.length?'none':mode==='name'?'match':top.score>=22&&margin>=7?'strong':margin<4?'ambiguous':'suggestion';
  let question=null;
  if(mode==='description'){
    if(!results.length)question='Explique qual produto ou serviço oferece e como atende seus clientes. Você também pode procurar pelo nome na lista.';
    else if(!op&&!vehicleRental&&!vehicleWash&&results.length>1&&confidence==='ambiguous')question='Você fabrica os produtos, vende para o consumidor, vende no atacado ou presta um serviço?';
    else if(confidence==='ambiguous')question='Encontrei mais de uma possibilidade. Confira as diferenças e escolha a que descreve sua atividade principal.';
  }
  if(consultancy?.question&&results.length){confidence='ambiguous';question=consultancy.question;}
  if(results.some(r=>r.requiresSubactivityConfirmation))question=[question,'Confirme também o tipo de imóvel: estar em prédio comercial não informa se o escritório fica no térreo ou em sobrado.'].filter(Boolean).join(' ');
  let clarification=null;
  const operations=[! /\b(atacado|atacadista)\b/.test(clean)&&/\b(vendo|vendemos|loja|varejo)\b/.test(clean)&&'retail',/\b(fabrico|fabricamos|produzo|produzimos)\b/.test(clean)&&'manufacture',/\b(conserto|reparo|manutencao)\b/.test(clean)&&'repair',/\b(atacado|atacadista)\b/.test(clean)&&'wholesale'].filter(Boolean);
  if(mode==='description'&&!consultancy&&!refinements.operation&&(new Set(operations).size>1||(!op&&!vehicleRental&&!vehicleWash&&results.length>1&&confidence==='ambiguous'))){
    clarification={type:'operation',options:Object.entries(REFINEMENTS.operation).map(([value,label])=>({value,label}))};
    question='Qual é a atividade principal deste negócio?';confidence='ambiguous';
  }
  if(mode==='description'&&medicine&&!/farmaci|drogari/.test(clean)&&!animal&&!/\b(pessoas|humanos?|humano)\b/.test(clean)&&!refinements.audience){
    clarification={type:'audience',options:Object.entries(REFINEMENTS.audience).map(([value,label])=>({value,label}))};
    question='Os medicamentos são para pessoas ou animais?';confidence='ambiguous';
  }
  if(vehicleSales&&results.length>1&&!refinements.vehicleBusiness){
    clarification={type:'vehicleBusiness',options:Object.entries(REFINEMENTS.vehicleBusiness).map(([value,label])=>({value,label}))};
    question='Você vende em uma agência/revenda independente ou em uma concessionária autorizada?';confidence='ambiguous';
  }
  if(consultancy?.question&&results.length){clarification={type:'specialty',options:Object.entries(REFINEMENTS.specialty).map(([value,label])=>({value,label}))};}
  else if(results.some(r=>r.requiresSubactivityConfirmation)&&!clarification){clarification={type:'premises',options:Object.entries(REFINEMENTS.premises).map(([value,label])=>({value,label}))};}
  return {results,confidence,question,clarification,evidence:{description:positiveDescription(original),operation:op,refinements},engine:'local-rules-tfidf-v3',vocabularyVersion:VOCABULARY_VERSION};
}

export function isValidSelection(catalog,activityId,subactivityId) {
  const activity=catalog.activities.find(a=>a.id===activityId);
  return Boolean(activity&&activity.subactivities.some(s=>s.id===subactivityId));
}
