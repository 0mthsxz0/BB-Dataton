/** Reviewed aliases; never changes catalog identifiers. */
export const VOCABULARY_VERSION = '2026-10-29.2';
export const ALIASES = [
  [/\b(frutas?|bananas?|macas?|verduras?|legumes?|hortifruti|sacolao)\b/g, 'produtos hortifrutigranjeiros'],
  [/\beletrodomesticos?\b/g, 'aparelhos uso domestico'],
  [/\b(carros?|automoveis|automovel|automobil[eo]s?)\b/g, 'veiculos automoveis'],
  [/\bmotos?\b/g, 'motocicletas'],
  [/\bbikes?\b/g, 'bicicletas'],
  [/\b(sapatos?|sandalias?|chinelos?|tenis)\b/g, 'calcados'],
  [/\b(oculos)\b/g, 'artigos optica'],
  [/\b(celulares?|smartphones?)\b/g, 'celulares equipamentos informatica'],
  [/\b(tvs?|televisoes|televisores)\b/g, 'televisores aparelhos uso domestico'],
  [/\b(geladeiras?|fogoes|fogao)\b/g, 'aparelhos uso domestico'],
  [/\b(tijolos?|cimento|areia para obras)\b/g, 'material de construcao'],
  [/\b(parafusos?|martelos?|alicates?)\b/g, 'ferragens ferramentas'],
  [/\b(pneus?)\b/g, 'pneumaticos pecas acessorios veiculos'],
  [/\b(joias?|bijus?)\b/g, 'joalheria bijuterias'],

  [/\bremedios?\b/g, 'medicamentos'],
  [/\bfarmacia?s?\b/g, 'farmacia'],
  [/\bdrograria\w*\b/g, 'drogaria'],
  [/\bmedicamento?s?\b/g, 'medicamentos'],
  [/\bcosmeticos?\b/g, 'cosmeticos perfumaria'],
  [/\bconcert(?:o|amos)\b/g, 'conserto'],
  [/\bcelualr\b/g, 'celular'],
  [/\bpizaria\b/g, 'pizzaria'],
];
export const REFINEMENTS = {
  vehicleBusiness: {agency:'Agência ou revenda independente de veículos',dealer:'Concessionária autorizada de veículos'},
  operation: {retail:'Vendo no varejo para consumidores', wholesale:'Vendo no atacado para revenda', manufacture:'Fabrico produtos', repair:'Faço conserto e manutenção', service:'Presto serviços'},
  specialty: {management:'Consultoria de gestão administrativa', finance:'Consultoria financeira contábil', software:'Consultoria de software', hardware:'Consultoria de equipamentos de informática', engineering:'Consultoria de engenharia', interiors:'Consultoria de decoração de interiores'},
  premises: {ground:'Escritório no térreo', townhouse:'Escritório em sobrado'},
  audience: {human:'Medicamentos para pessoas', animal:'Medicamentos veterinários para animais'},
};
export function validRefinements(value) {
  return value && typeof value==='object' && !Array.isArray(value) && Object.entries(value).every(([key,answer])=>Object.hasOwn(REFINEMENTS,key)&&typeof answer==='string'&&Object.hasOwn(REFINEMENTS[key],answer));
}

export const CONCEPTS = [
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
