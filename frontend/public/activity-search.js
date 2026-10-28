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
const CONCEPTS = [
  {pattern:/\b(pizza\w*|restaurante\w*|churrasc\w*|cantina\w*|marmit\w*|refeic\w*|comida pronta|almoco|jantar)\b/, terms:'restaurantes churrascarias pizzarias cantinas alimentacao', ids:['625'], reason:'preparo e venda de refeições'},
  {pattern:/\b(padaria\w*|pao|paes|confeitar\w*|bolos?|doces?|bomboni\w*|panifica\w*)\b/,terms:'padarias bombonieres confeitarias',ids:['470'],reason:'panificação ou confeitaria'},
  {pattern:/\b(barbear\w*|barbeir\w*|cabel\w*|manicure|pedicure|unhas?|salao de beleza)\b/,terms:'cabeleireiros barbeiros saloes beleza manicure pedicure',ids:['641'],reason:'serviços de beleza e cuidados pessoais'},
  {pattern:/\b(roupas?|vestuari\w*|camisetas?|vestidos?|brecho|boutique|moda)\b/,terms:'vestuario roupas',reason:'vestuário'},
  {pattern:/\b(costur\w*|ajust\w* de roupas?|conserto de roupas?|bainhas?)\b/,terms:'reparacao artigos acessorios vestuario tecidos',ids:['636'],reason:'conserto e ajuste de roupas'},
  {pattern:/\b(mercadinho|merceari\w*|supermercad\w*|minimercad\w*|alimentos e limpeza)\b/,terms:'mercearias supermercados comercio varejista mercadorias geral',ids:['909'],reason:'comércio de mercadorias de consumo diário'},
  {pattern:/\b(advoga\w*|juridic\w*|contabil\w*|contador\w*|contabilidade|auditoria)\b/,terms:'servicos escritorio juridicos contabeis auditoria',ids:['674'],reason:'serviços jurídicos, contábeis ou de escritório'},
  {pattern:/\b(dentist\w*|odont\w*|consultorio dentario)\b/,terms:'servicos odontologicos',ids:['690'],reason:'atendimento odontológico'},
  {pattern:/\b(program\w*|software|aplicativo\w*|sistemas? web|sites?|desenvolvedor\w*)\b/,terms:'desenvolvimento programas computador',ids:['1006','1008'],reason:'desenvolvimento de programas de computador'},
  {pattern:/\b(computador\w*|notebook\w*|informatica|celular\w*|smartphone\w*|impressor\w*)\b/,terms:'computadores equipamentos informatica perifericos',reason:'equipamentos de informática'},
  {pattern:/\b(consert\w*|repar\w*|manutenc\w*|assistencia tecnica)\b/,terms:'manutencao reparacao',reason:'reparação ou manutenção'},
  {pattern:/\b(farmaci\w*|drogari\w*|medicament\w*)\b/,terms:'farmacias drogarias',ids:['476'],reason:'farmácia ou drogaria'},
  {pattern:/\b(lavander\w*|lavo roupas|lavamos roupas|lavagem de roupas|tinturari\w*)\b/,terms:'lavanderias tinturarias',ids:['640'],reason:'lavagem e tratamento de roupas'},
  {pattern:/\b(imobiliari\w*|alugo imoveis|locacao de imoveis|corretor de imoveis)\b/,terms:'servicos locacao arrendamento intermediacao bens imoveis',ids:['694'],reason:'intermediação ou locação de imóveis'},
  {pattern:/\b(creche\w*|escola\w*|educacao infantil|ensino fundamental)\b/,terms:'ensino pre escolar fundamental medio',ids:['728'],reason:'ensino ou educação infantil'},
  {pattern:/\b(bar|bares|boteco\w*|cafeteria\w*|cafe)\b/,terms:'bares botequins cafes',ids:['626'],reason:'bar ou cafeteria'},
  {pattern:/\b(academia\w*|musculacao|personal trainer|fitness|pilates)\b/,terms:'academia ginastica esporte',reason:'atividade física e ginástica'},
  {pattern:/\b(pet ?shop|banho e tosa|racao|animais de estimacao)\b/,terms:'animais estimacao pet veterinarios',reason:'produtos ou serviços para animais de estimação'},
  {pattern:/\b(oficina mecanica|consert\w* carros?|mecanico|funilaria|automotiv\w*)\b/,terms:'reparacao manutencao veiculos automotores mecanica funilaria',reason:'reparação de veículos'},
  {pattern:/\b(marcenari\w*|moveis|mobiliario|armarios? planejados?)\b/,terms:'moveis madeira',reason:'móveis e mobiliário'},
];

export function createActivityIndex(catalog) {
  const entries=catalog.activities.map(activity=>{
    const text=activity.label;
    const ts=tokens(text);
    return {activity,normalized:normalize(text),tokens:ts,bag:new Set(ts)};
  });
  const frequency=new Map();
  for(const row of entries)for(const word of row.bag)frequency.set(word,(frequency.get(word)||0)+1);
  return {entries,frequency,size:entries.length};
}

function grams(text){const t=' '+normalize(text)+' ';const g=new Set();for(let i=0;i<t.length-2;i++)g.add(t.slice(i,i+3));return g;}
function similarity(a,b){const aa=grams(a),bb=grams(b);let n=0;for(const g of aa)if(bb.has(g))n++;return 2*n/(aa.size+bb.size||1);}
function idf(index,word){return Math.log(1+(index.size+1)/((index.frequency.get(word)||0)+1));}
function negatedText(text){return text.replace(/\b(?:nao|nunca)\s+(?:fabrico|fabricamos|produzo|produzimos|vendo|vendemos|conserto|consertamos|somos|somos uma)\b(?:\s+\w+){0,2}/g,' ');}
function operation(text){
  const cleaned=negatedText(normalize(text));
  if(/\b(conserto|consertamos|reparo|reparamos|manutencao|assistencia tecnica)\b/.test(cleaned))return 'repair';
  if(/\b(fabrico|fabricamos|produzo|produzimos|fabricacao|fabrica|industria)\b/.test(cleaned))return 'manufacture';
  if(/\b(atacado|atacadista|distribuidora|distribuimos)\b/.test(cleaned))return 'wholesale';
  if(/\b(vendo|vendemos|revendo|revendemos|loja|varejo|varejista|comercializo|comercializamos|comercio)\b/.test(cleaned))return 'retail';
  return null;
}
function candidateOperation(label){if(label.startsWith('fabricacao')||label.startsWith('confeccao'))return 'manufacture';if(label.includes('atacadista'))return 'wholesale';if(label.includes('varejista'))return 'retail';if(/reparacao|manutencao/.test(label))return 'repair';return null;}

/** Returns only identifiers belonging to the supplied parent/subactivity catalog. */
export function searchActivities(index, query, {mode='name',limit=12}={}) {
  const q=normalize(query);
  if(!q)return {results:mode==='name'?index.entries.slice(0,limit).map(x=>({activity:x.activity,score:0,reason:'Lista de atividades'})):[],confidence:'none',question:mode==='description'?'Conte o que você vende, produz ou faz e quem são seus clientes.':null};
  const rawTokens=tokens(query);
  if(mode==='description'&&rawTokens.length<2)return {results:[],confidence:'none',question:'Conte o que você vende, produz ou faz e quem são seus clientes.'};
  const clean=negatedText(q);
  const concepts=mode==='description'?CONCEPTS.filter(c=>c.pattern.test(clean)):[];
  const additions=concepts.flatMap(c=>tokens(c.terms));
  const qtokens=[...new Set([...rawTokens,...additions])];
  const op=operation(query);
  const ranked=[];
  for(const row of index.entries){
    let score=0;const matches=[];
    for(const token of qtokens){
      const exact=row.bag.has(token);
      const prefix=!exact&&token.length>=4&&[...row.bag].some(w=>w.startsWith(token)||token.startsWith(w)&&w.length>=4);
      if(exact||prefix){score+=idf(index,token)*(exact?1:.65)*(rawTokens.includes(token)?1:.65);matches.push(token);}
    }
    if(row.normalized.includes(q))score+=15;
    if(row.activity.id===query.trim())score+=40;
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
    const cop=candidateOperation(row.normalized);
    if(op&&cop)score+=op===cop?8:-18;
    // Common-language descriptions disambiguate software product vs custom work.
    if(row.activity.id==='1008'&&/sob encomenda|sob medida|para clientes/.test(q))score+=15;
    if(row.activity.id==='1006'&&/produto proprio|licenc|comercializ/.test(q))score+=15;
    if(row.activity.id==='1007'&&op==='repair'&&/computador|notebook|informatica|celular|smartphone/.test(q))score+=22;
    if(mode==='name'&&score<3&&qtokens.length<=3){const fuzzy=Math.max(...qtokens.map(t=>Math.max(0,...row.tokens.map(w=>similarity(t,w)))));if(fuzzy>.62)score+=fuzzy*5;}
    if(score<=0)continue;
    const subCandidates=row.activity.subactivities.map(s=>{
      const st=new Set(tokens(s.label));let subScore=0;for(const t of qtokens)if(st.has(t))subScore+=idf(index,t);
      if(normalize(s.label).includes(q))subScore+=10;
      return {subactivity:s,score:subScore};
    }).sort((a,b)=>b.score-a.score||a.subactivity.label.localeCompare(b.subactivity.label,'pt-BR'));
    const sub= subCandidates.length===1 ? subCandidates[0].subactivity : subCandidates[0]?.score>0&&(subCandidates[0].score-(subCandidates[1]?.score||0))>=2 ? subCandidates[0].subactivity : null;
    const reason=concepts.filter(c=>c.ids?.includes(row.activity.id)).map(c=>c.reason).join('; ')|| (matches.length?`Termos relacionados: ${[...new Set(matches)].slice(0,4).join(', ')}`:'Nome aproximado');
    ranked.push({activity:row.activity,subactivity:sub,score,reason,subactivityReason:subCandidates.length===1?'Única subatividade vinculada a esta atividade no catálogo':sub?'Descrição compatível com a subatividade':'Escolha a subatividade para confirmar'});
  }
  ranked.sort((a,b)=>b.score-a.score||a.activity.label.localeCompare(b.activity.label,'pt-BR'));
  const top=ranked[0],margin=top?(top.score-(ranked[1]?.score||0)):0;
  const sufficient=mode==='name'||(top&&top.score>=12&&(concepts.length>0||rawTokens.filter(t=>top.activity.label&&tokens(top.activity.label).includes(t)).length>=2));
  const results=sufficient?(mode==='description'?ranked.filter(r=>r.score>=Math.max(8,(top?.score||0)*.4)):ranked).slice(0,limit):[];
  const confidence=!results.length?'none':mode==='name'?'match':top.score>=22&&margin>=7?'strong':margin<4?'ambiguous':'suggestion';
  let question=null;
  if(mode==='description'){
    if(!results.length)question='Explique qual produto ou serviço oferece e como atende seus clientes. Você também pode procurar pelo nome na lista.';
    else if(!op&&results.length>1&&confidence==='ambiguous')question='Você fabrica os produtos, vende para o consumidor, vende no atacado ou presta um serviço?';
    else if(confidence==='ambiguous')question='Encontrei mais de uma possibilidade. Confira as diferenças e escolha a que descreve sua atividade principal.';
  }
  return {results,confidence,question};
}

export function isValidSelection(catalog,activityId,subactivityId) {
  const activity=catalog.activities.find(a=>a.id===activityId);
  return Boolean(activity&&activity.subactivities.some(s=>s.id===subactivityId));
}
