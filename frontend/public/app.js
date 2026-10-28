const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const escape = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paths = {
  shield: '<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
  building: '<path d="M4 21V5h10v16M14 10h6v11M2 21h20M8 9h2M8 13h2M8 17h2M17 14h1M17 18h1"/>',
  home: '<path d="m3 10 9-7 9 7M5 9v12h14V9M9 21v-7h6v7"/>',
  heart: '<path d="M20 5c-3-3-7 0-8 2-1-2-5-5-8-2-5 5 3 11 8 15 5-4 13-10 8-15Z"/>',
  car: '<path d="m4 10 2-6h12l2 6M3 10h18v8H3ZM6 18v3M18 18v3M6 14h2M16 14h2"/>',
  leaf: '<path d="M20 3C8 2 2 8 5 16c8 5 16 0 15-13ZM3 21 16 8M9 15v-5M9 15h5"/>',
  phone: '<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M10 18h4M10 5h4"/>',
  search: '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
  person: '<circle cx="12" cy="7" r="3"/><path d="M5 21v-3c0-6 14-6 14 0v3M17 10l2 2 3-3"/>',
  chat: '<path d="M21 11a9 9 0 0 1-13 8l-5 2 1-5A9 9 0 1 1 21 11Z"/><path d="m8 8 2 3 3 2 3-2"/>',
  card: '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 3"/>',
  gift: '<path d="M3 9h18v4H3ZM5 13v8h14v-8M12 9v12"/><path d="M12 9C3 9 5 1 9 4l3 5c9 0 7-8 3-5Z"/>',
  camera: '<rect x="3" y="5" width="14" height="11" rx="2"/><path d="m17 8 4-2v9l-4-2M10 16v5M6 21h8"/>',
  laptop: '<path d="M5 17V4h14v13M2 17h20l-2 3H4Z"/>',
  alarm: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M9 2h6M9 22h6"/>',
  arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  clipboard: '<rect x="5" y="5" width="14" height="17" rx="2"/><rect x="9" y="2" width="6" height="5" rx="1"/><path d="m9 14 2 2 4-5"/>'
};
const icon = (name) => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.shield}</svg>`;
const external = (url, label, cls = '') => `<a class="${cls}" href="${escape(url)}" target="_blank" rel="noopener noreferrer">${label}<span class="sr-only"> (abre em outra aba)</span></a>`;
const enterprise = '/seguros/seguro-empresarial';
const official = 'https://www.bbseguros.com.br';
let data;
let currentPage;
let slide = 0;
let category = 'Todos';
let compareType = 'coverages';
let dialogTrigger;
let toastTimer;

const products = [
  { name:'Residencial', prefix:'Seguro', category:'Pra você', icon:'home', text:'Tudo o que você precisa para manter seu lar protegido. Um seguro flexível e completo.', url:official+'/seguros/seguro-residencial' },
  { name:'Vida', prefix:'Seguro de', category:'Pra você', icon:'heart', text:'Você e sua família com proteção para aproveitar tudo o que a vida pode oferecer.', url:official+'/seguros/seguro-vida' },
  { name:'Doenças Graves', prefix:'Seguro para', category:'Pra você', icon:'shield', text:'Proteção financeira e prevenção para cuidar de você e de quem você ama.', url:official+'/seguros/doencas-graves' },
  { name:'Empresarial', prefix:'Seguro', category:'Para empresas', icon:'building', text:'Criado para proteger seu patrimônio, assegurar seus resultados e garantir a sua tranquilidade.', url:enterprise },
  { name:'Agrícola Flex', prefix:'Seguro', category:'Para o rural', icon:'leaf', text:'Proteção para a produção agrícola, do plantio à colheita.', url:official+'/seguros/seguro-rural/seguro-agricola-flex' },
  { name:'Itens Pessoais', prefix:'Seguro de', category:'Pra você', icon:'phone', text:'Proteção para os itens que acompanham você no dia a dia.', url:official+'/seguros/para-voce/seguro-itens-pessoais' },
  { name:'Auto', prefix:'Seguro', category:'Pra você', icon:'car', text:'Proteja seu carro, moto, táxi ou caminhão com a BB Seguros.', url:official+'/seguros/para-voce/auto' }
  ,{ name:'Proteção Pessoal', prefix:'Seguro', category:'Pra você', icon:'person', text:'Uma proteção pensada para diferentes estágios da sua vida.', url:official+'/seguros/para-voce/vida/protecao-pessoal' }
  ,{ name:'Júnior', prefix:'Brasilprev', category:'Mais soluções', icon:'leaf', text:'Conheça a solução de previdência Brasilprev Júnior.', url:official+'/previdencia' }
  ,{ name:'Único', prefix:'Ourocap', category:'Mais soluções', icon:'gift', text:'Conheça as opções de capitalização Ourocap.', url:'https://www.bb.com.br/pbb/pagina-inicial/voce/produtos-e-servicos/capitalizacao#/' }
];
const articles = [
  ['Assistências do Seguro Empresarial: como acionar na BB Seguros','assistencias-seguro-empresarial','clipboard'],
  ['Planejamento anual: por que incluir o Seguro Empresarial no orçamento de 2027?','planejamento-anual-seguro-empresarial','card'],
  ['Coworking para equipes: como estruturar o trabalho híbrido com segurança?','coworking-para-equipes','building'],
  ['Danos a terceiros na empresa: como se proteger e evitar prejuízos financeiros','educacao-financeira','shield'],
  ['O que é CSLL e como o imposto funciona para empresas?','csll-o-que-e','card'],
  ['Desratização em empresas: entenda as diferenças no controle de pragas','desratizacao','home'],
  ['Seguro Empresarial BB Seguros: te mostramos 15 motivos para contratar','seguro-empresarial-bb-seguros','shield'],
  ['O que é e quando fazer a manutenção preventiva da sua empresa?','manutencao-preventiva','clock'],
  ['Como agir em caso de incêndio na sua empresa e como se proteger com segurança?','incendio-em-empresa','alarm'],
  ['Por que contratar o Seguro Empresarial com cobertura para delivery é essencial para quem trabalha com entregas','seguro-delivery','car'],
  ['10 mitos e verdades sobre o Seguro Empresarial','mitos-e-verdades-seguro-empresarial','chat'],
  ['O que é apólice de seguro? Um guia completo!','apolice-de-seguros','clipboard']
];
const slides = [
  { eyebrow:'Para quem faz acontecer', title:'Seu negócio protegido.<br>Você mais tranquilo.', text:'Conheça o Seguro Empresarial e encontre um plano para cuidar do que você construiu.', cta:'Conheça o Seguro Empresarial', href:enterprise },
  { eyebrow:'Proteção em cada conquista', title:'O que importa para você<br>importa pra gente.', text:'Soluções para você, sua família, sua empresa e seu negócio no campo.', cta:'Encontre seu seguro', href:'#solucoes' },
  { eyebrow:'Planos para sua empresa', title:'Mais proteção para<br>seguir em frente.', text:'Compare os planos Essencial, Prático e Total e conheça as coberturas disponíveis.', cta:'Compare os planos', href:enterprise+'#comparar' }
];
const faq = [
  ['Quem tem direito ao Seguro Empresarial BB Seguros?', 'O produto é destinado a empresas de diferentes portes e segmentos. A página oficial informa que a contratação pode ser feita por pessoa física ou jurídica. Consulte os canais oficiais para confirmar as condições de aceitação.'],
  ['Como posso contatar a BB Seguros em caso de dúvidas ou sinistro?', 'Utilize os canais oficiais de atendimento da BB Seguros para tirar dúvidas, comunicar um sinistro ou solicitar assistência.'],
  ['Como atualizar os meus dados cadastrais?', 'Solicite a atualização pelos canais oficiais de atendimento. Algumas mudanças exigem uma alteração no contrato, chamada endosso.'],
  ['Eu posso alterar, incluir ou excluir minhas coberturas?', 'Entre em contato com a equipe de atendimento para verificar as possibilidades e condições de alteração das coberturas contratadas.'],
  ['Posso alterar o plano do meu Seguro Empresarial?', 'Segundo o FAQ consultado em 27/10/2026, não é possível alterar o plano do Seguro Empresarial. Consulte os canais de atendimento para mais informações.'],
  ['Como faço para alterar o endereço do meu seguro?', 'A mudança de endereço exige uma solicitação de endosso à Central de Contratação, Renovação e Alteração de Apólices. Mantenha o endereço atualizado para a efetividade das coberturas.'],
  ['Qual cobertura é ideal para meu negócio?', 'A escolha depende da atividade e das necessidades da sua empresa. Compare os planos e confirme os detalhes com a equipe oficial de atendimento.'],
  ['Posso alterar a forma de pagamento?', 'A página oficial informa que a forma de pagamento pode ser alterada, exceto quando o pagamento é feito com cartão de crédito. Consulte o atendimento sobre as condições.'],
  ['Como faço a renovação do meu seguro?', 'O FAQ oficial informa renovação automática, com aviso ao segurado 45 dias antes do vencimento para que possa optar por renovar ou não o contrato.'],
  ['Como faço o cancelamento do meu seguro?', 'Solicite a alteração do contrato pelos canais oficiais da Central de Contratação, Renovação e Alteração de Apólices.']
];

function header() {
  const home = currentPage === 'home';
  $('#header').innerHTML = `<div class="topbar container">
    <a href="${enterprise}" data-route>${icon('clipboard')}Contratar um Seguro</a>
    ${external(official+'/acionar-seguro',icon('shield')+'Acionar e Acompanhar')}
    ${external('https://security-oauth.bbseguros.com.br/',icon('chat')+'Solicitar Assistência')}
  </div><nav class="nav" aria-label="Navegação principal"><div class="container nav-inner">
    <a href="/" data-route class="brand" aria-label="BB Seguros, página inicial"><span class="brand-symbol" aria-hidden="true">▱</span>BB <em>Seguros</em></a>
    <button class="icon-button mobile-toggle" aria-expanded="false" aria-controls="nav-links" aria-label="Abrir menu">${icon('menu')}</button>
    <div class="nav-links" id="nav-links">
      <details><summary>${home?'Seguros':'Pra Você'}</summary><div class="dropdown"><a href="/#solucoes" data-route>Conheça nossos seguros</a><a href="${enterprise}" data-route>Seguro Empresarial</a>${external(products[0].url,'Seguro Residencial')}${external(products[1].url,'Seguro de Vida')}${external(products[5].url,'Seguro Auto')}</div></details>
      <details><summary>${home?'Previdência':'Para Empresas'}</summary><div class="dropdown">${home?external('https://www1.brasilprev.com.br/','Conheça a Brasilprev'):`<a href="${enterprise}" data-route>Seguro Empresarial</a><a href="${enterprise}#planos" data-route>Conheça os planos</a><a href="${enterprise}#comparar" data-route>Compare coberturas</a>`}</div></details>
      <details><summary>${home?'Capitalização':'Para o Rural'}</summary><div class="dropdown">${home?external('https://www.brasilcap.com.br/','Conheça a Brasilcap'):external(official+'/seguros/seguro-rural','Conheça os Seguros Rurais')}</div></details>
      <details><summary>${home?'Planos Odontológicos':'Central de Ajuda'}</summary><div class="dropdown">${home?external('https://www.bbdental.com.br/','Conheça os planos'):`<a href="${enterprise}#duvidas" data-route>Perguntas frequentes</a>${external(official+'/seguros/ajuda/atendimento','Fale com a gente')}`}</div></details>
      ${external(home?official+'/portal-parceiros':'https://security-oauth.bbseguros.com.br/',icon('person')+(home?'Portal Parceiros':'Área do Cliente'),'nav-link client')}
      <button class="icon-button search-button" aria-label="Buscar seguros">${icon('search')}</button>
    </div></div></nav>`;
  $('.mobile-toggle').addEventListener('click', (e) => {
    const button = e.currentTarget;
    const open = button.getAttribute('aria-expanded') !== 'true';
    button.setAttribute('aria-expanded', String(open));
    button.setAttribute('aria-label', open?'Fechar menu':'Abrir menu');
    $('#nav-links').classList.toggle('open', open);
  });
  $('.search-button').addEventListener('click', openSearch);
  $$('.nav details').forEach(d => d.addEventListener('toggle', () => { if(d.open) $$('.nav details').filter(other=>other!==d).forEach(other=>other.open=false); }));
}

function footer() {
  $('#footer').innerHTML = `<div class="footer-main"><div class="container footer-grid">
    <div class="footer-brand"><a class="brand" href="/" data-route>BB Seguros</a><p class="muted">Proteção para cada conquista.</p><p class="muted">Estudo independente de interface.<br>Imagem ilustrativa gerada com IA.</p></div>
    <div><h3>PARA VOCÊ</h3><ul>${products.filter(p=>p.category==='Pra você').map(p=>`<li>${external(p.url,'Seguro '+p.name)}</li>`).join('')}</ul></div>
    <div><h3>PARA EMPRESAS</h3><ul><li><a href="${enterprise}" data-route>Seguro Empresarial</a></li><li><a href="${enterprise}#planos" data-route>Conheça os planos</a></li><li><a href="${enterprise}#comparar" data-route>Compare coberturas</a></li><li><a href="${enterprise}#duvidas" data-route>Perguntas frequentes</a></li></ul></div>
    <div><h3>FALE COM A GENTE</h3><ul><li>${external(official+'/seguros/ajuda/atendimento','Canais de atendimento')}</li><li>${external(official+'/politica-de-privacidade','Política de privacidade')}</li><li>${external(official,'Site oficial BB Seguros ↗')}</li><li>${external('https://api.whatsapp.com/send?phone=551140047000&text=Oi&app_absent=0','WhatsApp oficial ↗')}</li></ul></div>
  </div></div><div class="footer-bottom"><div class="container"><p>Protótipo para estudo • Conteúdo público consultado em 27/10/2026 • Sem vínculo com o portal oficial.</p><button id="reset-cookies">Preferências de cookies</button></div></div>`;
  $('#reset-cookies').addEventListener('click', openCookiePreferences);
}

function homePage() {
  $('#main').innerHTML = `<section class="hero home-hero" aria-roledescription="carrossel" aria-label="Destaques"><div class="container"><div id="home-slide"></div><div class="carousel-controls"><button class="carousel-arrow" data-slide-step="-1" aria-label="Destaque anterior">‹</button>${slides.map((_,i)=>`<button class="dot" data-slide="${i}" aria-label="Ir para destaque ${i+1}" aria-current="${i===slide}"></button>`).join('')}<button class="carousel-arrow" data-slide-step="1" aria-label="Próximo destaque">›</button></div></div></section>
    <section class="section" id="solucoes"><div class="container"><div class="section-head"><p class="eyebrow">A proteção que combina com você</p><h2>Para cada conquista,<br>uma solução.</h2><p>Conheça as soluções que a BB Seguros oferece para proteger o que é importante para você.</p></div><div class="product-tools"><div class="filter-chips" role="group" aria-label="Filtrar seguros por público">${['Todos','Pra você','Para empresas','Para o rural'].map(c=>`<button class="chip" data-category="${c}" aria-pressed="${c===category}">${c}</button>`).join('')}</div><label class="field"><span>Encontre seu seguro</span><input type="search" id="product-search" placeholder="Busque por nome ou proteção"></label></div><p class="result-count" id="product-count" aria-live="polite"></p><div class="products" id="products"></div></div></section>
    <section class="section benefit-band"><div class="container"><div><p class="eyebrow">Você ainda mais protegido</p><h2>Proteção que faz parte<br>da sua vida.</h2><p>A BB Seguros reúne seguros e soluções para diferentes momentos. Conheça os benefícios para quem já é cliente.</p>${external(official+'/superprotegido','Conheça o Superprotegido '+icon('arrow'),'btn')}</div><div class="protection-art">${icon('shield')}</div></div></section>
    <section class="section"><div class="container"><div class="section-head"><h2>Juntos pelas suas conquistas</h2><p>Da sua casa ao seu negócio, a proteção acompanha você.</p></div><div class="stats"><div class="stat"><strong>+1 milhão</strong><span>de lares segurados</span></div><div class="stat"><strong>+3 mil</strong><span>acionamentos por dia</span></div><div class="stat"><strong>+5 mil</strong><span>cidades no Brasil</span></div></div><p class="disclaimer">Indicadores exibidos na página inicial oficial na data da consulta.</p></div></section>
    <section class="section benefit-band"><div class="container" style="display:block"><div class="section-head"><h2>Saiba mais sobre a BB Seguros</h2></div><div class="institutional-links">${[
      ['Histórias felizes de seguros','/historias-felizes-de-seguros','heart'],['Patrocínios e Eventos','/seguros/patrocinios-eventos','gift'],['Vantagens BB Seguros','/vantagens-bb-seguros','shield'],['Sustentabilidade','/seguros/sustentabilidade','leaf'],['Inovação','/inovacao','laptop'],['Blog Papo Seguro','/seguros/blog','clipboard']
    ].map(([name,url,ic])=>external(official+url,icon(ic)+name+' ↗')).join('')}</div></div></section>`;
  renderSlide(); renderProducts();
  $$('[data-slide]').forEach(b=>b.addEventListener('click',()=>{slide=Number(b.dataset.slide);renderSlide();}));
  $$('[data-slide-step]').forEach(b=>b.addEventListener('click',()=>{slide=(slide+Number(b.dataset.slideStep)+slides.length)%slides.length;renderSlide();}));
  $$('[data-category]').forEach(b=>b.addEventListener('click',()=>{category=b.dataset.category;$$('[data-category]').forEach(c=>c.setAttribute('aria-pressed',String(c.dataset.category===category)));renderProducts();}));
  $('#product-search').addEventListener('input',renderProducts);
}

function renderSlide() {
  const s=slides[slide];
  $('#home-slide').innerHTML=`<div class="hero-grid"><div><p class="eyebrow">${s.eyebrow}</p><h1>${s.title}</h1><p>${s.text}</p><div class="hero-actions"><a class="btn btn-coral" href="${s.href}" data-route>${s.cta} ${icon('arrow')}</a></div></div><img class="hero-photo" src="/entrepreneur.png" width="1448" height="1086" alt="Empreendedora preparando pedidos na sua loja, imagem ilustrativa gerada com IA" fetchpriority="high"></div>`;
  $$('[data-slide]').forEach(b=>b.setAttribute('aria-current',String(Number(b.dataset.slide)===slide)));
}

function normalize(t){ return t.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g,''); }
function renderProducts() {
  const q=normalize($('#product-search').value);
  const selected=products.filter(p=>(category==='Todos'||p.category===category)&&normalize(p.name+' '+p.text).includes(q));
  $('#product-count').textContent=`${selected.length} ${selected.length===1?'solução encontrada':'soluções encontradas'}`;
  $('#products').innerHTML=selected.length?selected.map(p=>`<article class="product"><div class="product-art">${p.name==='Empresarial'?'<img src="/entrepreneur.png" loading="lazy" alt="Empreendedora em sua loja">':icon(p.icon)}</div><div class="product-content"><small>${p.prefix}</small><h3>${p.name}</h3><p>${p.text}</p><div class="product-actions">${p.url===enterprise?`<a class="text-link" href="${enterprise}" data-route>Conheça ${icon('arrow')}</a><button class="text-link quote-trigger" style="border:0;background:none;color:var(--deep);padding:0">Faça cotação</button>`:external(p.url,'Conheça '+icon('arrow'),'text-link')}</div></div></article>`).join(''):'<p class="empty">Nenhum seguro encontrado. Experimente outro termo ou público.</p>';
  bindQuoteButtons($('#products'));
}

function enterprisePage() {
  $('#main').innerHTML=`<section class="hero"><div class="container"><nav class="breadcrumbs" aria-label="Você está aqui"><a href="/" data-route>Página Inicial</a><span aria-hidden="true">›</span><a href="/seguros" data-route>Seguros</a><span aria-hidden="true">›</span><span aria-current="page">Seguro Empresarial</span></nav><div class="hero-grid"><div><h1>Seguro Empresarial</h1><p>O Seguro Empresarial foi criado para proteger seu patrimônio, assegurar seus resultados e garantir a sua tranquilidade.</p><div class="hero-actions"><button class="btn btn-coral quote-trigger">Faça sua cotação ${icon('arrow')}</button><a href="#planos" class="text-link">Conheça os planos</a></div><p class="hero-foot">Seu negócio não pode parar. Conte com a gente.</p></div><img class="hero-photo" src="/entrepreneur.png" width="1448" height="1086" fetchpriority="high" alt="Empreendedora sorrindo enquanto prepara pedidos no seu negócio, imagem ilustrativa gerada com IA"></div></div></section>
    <nav class="jumpnav" aria-label="Seções do seguro empresarial"><div class="container"><a href="#planos">Nossos planos</a><a href="#vantagens">Vantagens</a><a href="#comparar">Coberturas e assistências</a><a href="#beneficios">Benefícios Premium</a><a href="#duvidas">Dúvidas frequentes</a></div></nav>
    <section class="section" id="planos"><div class="container"><div class="section-head"><p class="eyebrow">Proteção do seu jeito</p><h2>Um plano para cada negócio.</h2><p>Escolha entre Essencial, Prático ou Total. Conheça as opções de proteção para o patrimônio da sua empresa.</p></div><div class="plans">${data.plans.map((p,i)=>`<article class="plan"><div class="plan-top"><h3>${escape(p.name)}</h3><p class="plan-count">${p.assistances} ASSISTÊNCIAS + ${p.coverageCount} COBERTURAS</p></div><div class="plan-body"><p class="plan-price-note">mensais a partir de</p><p class="plan-price">${escape(p.price)}<sup>*</sup></p><ul><li>Proteção para seu patrimônio</li><li>Assistências para o dia a dia</li><li>${i===2?'Benefícios Premium disponíveis':i===1?'Mais opções de proteção':'Coberturas essenciais'}</li></ul><button class="btn quote-trigger" data-plan="${p.id}">Simule online</button><button class="text-link" style="border:0;background:none;color:var(--deep);padding:0" data-plan-detail="${p.id}">Conheça o plano ${icon('arrow')}</button></div></article>`).join('')}</div><p class="disclaimer">*Valor poderá variar de acordo com o perfil. Valores e contadores reproduzidos da página pública consultada em 27/10/2026. A cotação válida é feita no canal oficial.</p></div></section>
    <section class="section feature-section" id="vantagens"><div class="container feature-grid"><div class="feature-intro"><p class="eyebrow">Seu negócio não pode parar</p><h2>Uma proteção<br>ainda mais completa.</h2><p>Das necessidades do dia a dia aos imprevistos, conheça as coberturas e os pacotes de assistências disponíveis para sua empresa.</p><a href="#comparar" class="text-link">Compare as opções ${icon('arrow')}</a></div><div class="feature-list">${[
      ['card','Pagamento facilitado','Débito, cartão de crédito, boleto e parcelamento.'],
      ['shield','Coberturas diferenciadas','Opções para home office, delivery e mercadorias em ambientes frigorificados.'],
      ['gift','Benefícios exclusivos','No plano Total, benefícios Premium. Limitado a 2 benefícios por CNPJ.'],
      ['clock','Assistências 24 horas','Conte com apoio para os imprevistos previstos no seu plano.']
    ].map(([ic,title,text])=>`<div class="feature-item">${icon(ic)}<h3>${title}</h3><p>${text}</p></div>`).join('')}</div></div></section>
    <section class="section" id="comparar"><div class="container"><div class="section-head"><p class="eyebrow">Escolha com clareza</p><h2>Compare e encontre seu plano.</h2><p>Veja as coberturas e assistências associadas a cada plano. Clique no nome de um item para entender sua descrição.</p></div><div class="toolbar"><label class="field"><span>Buscar na comparação</span><input type="search" id="coverage-search" placeholder="Ex.: incêndio, delivery, eletricista"></label><div class="tabs" role="tablist" aria-label="Tipo de proteção"><button role="tab" id="tab-coverages" aria-selected="${compareType==='coverages'}" aria-controls="comparison-panel" data-compare="coverages">Coberturas</button><button role="tab" id="tab-assistances" aria-selected="${compareType==='assistances'}" aria-controls="comparison-panel" data-compare="assistances">Assistências</button></div></div><p class="result-count" id="coverage-count" aria-live="polite"></p><div role="tabpanel" id="comparison-panel" aria-labelledby="tab-${compareType}" tabindex="0"><div class="table-wrap" id="comparison-table"></div></div><p class="disclaimer">A presença de um item indica sua associação no catálogo público, sujeita às condições do produto. Itens marcados como “Extra” exigem confirmação de contratação. Não são exibidos limites de indenização não confirmados.</p><p class="disclaimer">Os contadores comerciais de coberturas e assistências não correspondem necessariamente à quantidade de linhas do catálogo público. Confirme a composição do plano no canal oficial.</p></div></section>
    <section class="section premium" id="beneficios"><div class="container"><div class="section-head"><p class="eyebrow">Para ir além</p><h2>Benefícios Premium</h2><p>Benefícios exclusivos que o Seguro Empresarial Total oferece à sua empresa.</p></div><div class="premium-grid">${[
      ['camera','Câmera de Vídeo','Monitore sua empresa e acesse imagens pelo smartphone, com instalação e notificações por movimento.'],
      ['laptop','Plataforma Minu Biz','Uma plataforma de recompensas para fortalecer o relacionamento entre a sua empresa e seus clientes.'],
      ['alarm','Detectores de fumaça','Dispositivos que identificam princípio de incêndio e disparam um alarme, oferecendo segurança extra.']
    ].map(([ic,title,text])=>`<article class="premium-item"><div class="premium-art">${icon(ic)}</div><h3>${title}</h3><p>${text}</p>${external('https://empresarial.bbseguros.com.br/','Saiba mais '+icon('arrow'),'text-link')}</article>`).join('')}</div></div></section>
    <section class="section" id="duvidas"><div class="container"><div class="faq-head"><div><p class="eyebrow">A gente descomplica</p><h2>Ficou na dúvida?<br>Chama a gente agora!</h2></div>${external('https://api.whatsapp.com/send?phone=551140047000&text=Oi&app_absent=0',icon('chat')+'Falar no WhatsApp','btn btn-outline')}</div><div class="faq">${faq.map(([q,a])=>`<details><summary>${q}</summary><p>${a} ${external(official+'/seguros/ajuda/atendimento','Acesse o atendimento oficial ↗')}.</p></details>`).join('')}</div></div></section>
    <section class="section blog-section"><div class="container"><div class="blog-heading"><div><p class="eyebrow">Conteúdo para o seu negócio</p><h2>Blog Papo Seguro</h2></div><div><button class="icon-button blog-prev" aria-label="Artigos anteriores">${icon('arrow')}</button><button class="icon-button blog-next" aria-label="Próximos artigos">${icon('arrow')}</button></div></div><div class="blog-track" id="blog-track" tabindex="0" aria-label="Artigos sobre empresas">${articles.map(([title,slug,ic],i)=>`<article class="product"><div class="product-art">${icon(ic)}</div><div class="product-content"><small>Empresa • Papo Seguro</small><h3>${escape(title)}</h3>${external(official+'/seguros/blog/empresa/'+slug,'Ler artigo '+icon('arrow'),'text-link')}</div></article>`).join('')}</div></div></section>
    <section class="contact-banner"><div class="container contact-inner"><div><h2>Vamos proteger suas conquistas?</h2><p>Conheça os planos e continue sua cotação no canal oficial.</p></div><button class="btn quote-trigger">Explorar os planos ${icon('arrow')}</button></div></section>`;
  renderComparison();
  $('#coverage-search').addEventListener('input',renderComparison);
  $$('[data-compare]').forEach(b=>{
    b.addEventListener('click',()=>selectCompare(b.dataset.compare));
    b.addEventListener('keydown',e=>{ if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const type=e.key==='Home'?'coverages':e.key==='End'?'assistances':compareType==='coverages'?'assistances':'coverages';selectCompare(type);$(`[data-compare="${type}"]`).focus();} });
  });
  selectCompare(compareType);
  $$('[data-plan-detail]').forEach(b=>b.addEventListener('click',()=>openPlan(b.dataset.planDetail)));
  bindQuoteButtons($('#main'));
  $('.blog-next').addEventListener('click',()=>$('#blog-track').scrollBy({left:$('#blog-track').clientWidth,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'}));
  $('.blog-prev').addEventListener('click',()=>$('#blog-track').scrollBy({left:-$('#blog-track').clientWidth,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'}));
}

function selectCompare(type) {
  compareType=type;
  $$('[data-compare]').forEach(b=>{const active=b.dataset.compare===type;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;});
  $('#comparison-panel').setAttribute('aria-labelledby','tab-'+type);
  renderComparison();
}

function renderComparison() {
  const list=data[compareType];
  const query=normalize($('#coverage-search').value);
  const rows=list.filter(c=>normalize(c.name).includes(query));
  $('#coverage-count').textContent=`${rows.length} ${compareType==='coverages'?'coberturas':'assistências'} encontradas`;
  $('#comparison-table').innerHTML=`<table><caption>${compareType==='coverages'?'Coberturas':'Assistências'} associadas aos planos • catálogo público de 27/10/2026</caption><thead><tr><th scope="col">${compareType==='coverages'?'Coberturas':'Assistências'}</th>${data.plans.map(p=>`<th scope="col">${escape(p.name.replace('Empresarial ',''))}<small>${escape(p.price)}* / mês</small></th>`).join('')}</tr></thead><tbody>${rows.length?rows.map(c=>`<tr><th scope="row"><button class="coverage-name" data-coverage="${c.id}">${escape(c.name)}</button></th>${data.plans.map(p=>{const has=(compareType==='coverages'?p.coverages:p.assistanceIds).includes(c.id);return `<td>${has?'<span class="check" role="img" aria-label="Associado ao plano">✓</span>':'<span class="dash" role="img" aria-label="Não associado ao plano">—</span>'}</td>`;}).join('')}</tr>`).join(''):'<tr><td colspan="4" class="empty">Nenhum item encontrado. Tente outro termo.</td></tr>'}</tbody></table>`;
  $$('[data-coverage]').forEach(b=>b.addEventListener('click',()=>{const c=list.find(x=>x.id===b.dataset.coverage);openDialog(`<p class="eyebrow">${compareType==='coverages'?'Cobertura':'Assistência'}</p><h2 id="dialog-title">${escape(c.name)}</h2><p>${escape(c.description)}</p><p class="small-note">Descrição do catálogo público consultado. A aplicação e os limites dependem das condições do produto.</p>`);}));
}

function bindQuoteButtons(root){ $$('.quote-trigger',root).forEach(b=>b.addEventListener('click',()=>openQuote(b.dataset.plan))); }
function openDialog(content) {
  dialogTrigger=document.activeElement;
  $('#dialog-body').innerHTML=content;
  $('#dialog').showModal();
  $('.dialog-close').focus();
}
function openPlan(id) {
  const p=data.plans.find(x=>x.id===id);
  const coverages=data.coverages.filter(c=>p.coverages.includes(c.id));
  openDialog(`<p class="eyebrow">Conheça seu plano</p><h2 id="dialog-title">${escape(p.name)}</h2><p>A partir de <strong>${escape(p.price)} por mês*</strong></p><p>Itens associados no catálogo público:</p><ul class="dialog-list">${coverages.map(c=>`<li>${escape(c.name)}</li>`).join('')}</ul><p class="small-note">*O valor varia conforme o perfil. Coberturas extras, limites e condições devem ser confirmados no canal oficial. O catálogo detalhado pode ter mais itens que o contador comercial.</p><div class="dialog-actions"><button class="btn" id="modal-quote">Explorar este plano</button>${external(p.detailUrl,'Ver plano no site oficial ↗','btn btn-outline')}</div>`);
  $('#modal-quote').addEventListener('click',()=>{const original=dialogTrigger;$('#dialog').close();openQuote(id);dialogTrigger=original;});
}

function openQuote(id) {
  location.assign('/cotacao'+(id?'?plano='+encodeURIComponent(id):''));
}

function openSearch() {
  openDialog(`<h2 id="dialog-title">Como podemos ajudar?</h2><label class="field"><span>Busque um seguro</span><input class="search-input" id="global-search" type="search" placeholder="Ex.: empresarial, vida, auto"></label><div class="search-results" id="search-results" aria-live="polite"></div>`);
  function update(){const q=normalize($('#global-search').value);const found=products.filter(p=>normalize(p.name+' '+p.text).includes(q));$('#search-results').innerHTML=found.length?found.map(p=>p.url===enterprise?`<a href="${enterprise}" data-route>Seguro ${p.name} ${icon('arrow')}</a>`:external(p.url,`Seguro ${p.name} ↗`)).join(''):'<p>Nenhum seguro encontrado.</p>';}
  update();$('#global-search').addEventListener('input',update);$('#global-search').focus();
}

function consentRead(){try{return JSON.parse(localStorage.getItem('bb-study-preferences'));}catch{return null;}}
function consentSave(choice){try{localStorage.setItem('bb-study-preferences',JSON.stringify({choice,at:new Date().toISOString()}));}catch{} $('#cookies').innerHTML='';}
function cookieBanner(){if(consentRead())return;$('#cookies').innerHTML=`<div class="cookie-banner" role="region" aria-label="Preferências de cookies"><p>Este protótipo usa apenas armazenamento local para lembrar sua preferência. Não possui cookies de publicidade ou ferramentas de rastreamento. Você pode aceitar, rejeitar ou revisar suas preferências a qualquer momento.</p><div class="cookie-actions"><button class="btn" id="accept-cookies">Permitir cookies</button><button class="btn btn-outline" id="reject-cookies">Rejeitar cookies</button><button class="btn btn-outline" id="cookie-settings">Preferências</button></div></div>`;$('#accept-cookies').addEventListener('click',()=>consentSave('accepted'));$('#reject-cookies').addEventListener('click',()=>consentSave('rejected'));$('#cookie-settings').addEventListener('click',openCookiePreferences);}
function openCookiePreferences(){openDialog(`<h2 id="dialog-title">Sua privacidade importa.</h2><p>O protótipo não inclui analytics, publicidade ou cookies de terceiros. Somente a preferência escolhida é guardada no seu navegador.</p><p>Preferência atual: <strong>${consentRead()?.choice==='accepted'?'permitidos':consentRead()?.choice==='rejected'?'rejeitados':'não definida'}</strong>.</p><div class="dialog-actions"><button class="btn" id="save-necessary">Salvar somente essenciais</button><button class="btn btn-outline" id="save-accepted">Permitir</button></div>`);$('#save-necessary').addEventListener('click',()=>{consentSave('rejected');$('#dialog').close();toast('Preferência salva.');});$('#save-accepted').addEventListener('click',()=>{consentSave('accepted');$('#dialog').close();toast('Preferência salva.');});}
function toast(text){clearTimeout(toastTimer);$('#toast').textContent=text;$('#toast').classList.add('visible');toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),3000);}

function render(){
  currentPage=location.pathname.startsWith(enterprise)?'enterprise':'home';
  document.title=currentPage==='enterprise'?'Seguro Empresarial | BB Seguros · Protótipo':'BB Seguros · Protótipo de estudo';
  header();currentPage==='home'?homePage():enterprisePage();footer();
}
function scrollToHash(){if(location.hash){const element=document.getElementById(decodeURIComponent(location.hash.slice(1)));element?.scrollIntoView();}else window.scrollTo({top:0,behavior:'instant'});}
function navigate(url){const target=new URL(url,location.origin);const changed=target.pathname!==location.pathname;history.pushState({},'',target.pathname+target.search+target.hash);if(changed)render();scrollToHash();if(changed&&!target.hash)$('#main').focus({preventScroll:true});}
document.addEventListener('click',e=>{const a=e.target.closest('a');if(!a||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||e.button!==0||a.target==='_blank')return;const url=new URL(a.href,location.origin);if(url.origin===location.origin&&['/','/seguros',enterprise,enterprise+'/'].includes(url.pathname)){e.preventDefault();if($('#dialog').open)$('#dialog').close();navigate(url.href);}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){$$('.nav details').forEach(d=>d.open=false);if($('.mobile-toggle')?.getAttribute('aria-expanded')==='true')$('.mobile-toggle').click();}});
$('.dialog-close').addEventListener('click',()=>$('#dialog').close());
$('#dialog').addEventListener('click',e=>{if(e.target===$('#dialog')){const r=$('#dialog').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('#dialog').close();}});
$('#dialog').addEventListener('close',()=>{if(dialogTrigger?.isConnected)dialogTrigger.focus({preventScroll:true});});
window.addEventListener('popstate',()=>{render();scrollToHash();});
try {
  const response=await fetch('/plans.json');
  if(!response.ok)throw new Error('Não foi possível carregar os planos.');
  data=await response.json();render();cookieBanner();scrollToHash();
}catch(error){$('#main').innerHTML=`<div class="error" role="alert"><h1>Não conseguimos carregar a página.</h1><p>${escape(error.message)}</p><button class="btn" id="retry">Tentar novamente</button></div>`;$('#retry').addEventListener('click',()=>location.reload());}
