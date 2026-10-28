import { indexEvidence, assetEvidence } from './report-evidence.js';
import { personalizationView } from './product-ui.js';
/** UI adapter: sends only underwriting inputs, never contact or payment fields. */
export const NUMERIC_FIELDS = [
  ['contentsValue','Bens e equipamentos, sem estoque (R$)'],
  ['equipmentValue','Desses bens, quanto é equipamento elétrico? (R$)'],
  ['stockValue','Estoque no local (R$)'],
  ['buildingValue','Reconstrução do imóvel, sem terreno (R$)'],
  ['glassValue','Reposição de vidros e espelhos (R$)'],
  ['employees','Quantidade de empregados nesta unidade'],
  ['payroll','Folha mensal desta unidade (R$)'],
  ['monthlyExpenses','Despesas fixas mensais da unidade (R$)'],
  ['monthlyRevenue','Faturamento mensal da empresa (R$)'],
  ['units','Quantidade de unidades da empresa'],
  ['rentValue','Aluguel mensal (R$)'],
];
export const money = value => value == null ? 'Não informado' : Number(value).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
export const points = value => Number(value).toLocaleString('pt-BR',{maximumFractionDigits:1});
const ORIGIN_LABELS = {bens_ponderados:'Bens no local',equipamentos_ponderados:'Equipamentos',
  estoque_medio_estimado:'Estoque',valor_vidros_reposicao_brl:'Vidros',valor_predio_reposicao_brl:'Reconstrução',
  folha_pagamento_mensal:'Folha mensal',despesa_fixa_mensal_estimada:'Despesas fixas',faturamento_mensal:'Faturamento',
  funcionarios_unidade_confirmados:'Empregados na unidade',quantidade_unidades:'Unidades da empresa',valor_aluguel_recorrente:'Aluguel'};
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export async function api(url, payload) {
  const response = await fetch(url, payload === undefined ? {cache:'no-store'} : {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload), signal:AbortSignal.timeout(35000),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Serviço indisponível. Tente novamente.');
  return data;
}

export function riskPayload(state, questionnaire) {
  const [empresaId, imovelId] = (state.sourceKey || '').split('|');
  const keys = ['activityId','subactivityId','otherSubactivity','protection','shopping','city','uf','cnae','glassCount',...NUMERIC_FIELDS.map(([key])=>key)];
  return {...Object.fromEntries(keys.map(k=>[k,state[k]])), empresaId:empresaId || '', imovelId:imovelId || '',
    answers:Object.fromEntries(questionnaire.groups.flatMap(g=>g.questions.map(q=>[q.id,state[q.id] === 'yes' ? true : state[q.id] === 'no' ? false : null])))};
}

const CUSTOMER_LABELS={
 contentsValue:'Quanto valem os móveis e equipamentos da empresa, sem os produtos em estoque? (R$)',
 equipmentValue:'Desse valor, quanto é de aparelhos e equipamentos elétricos? (R$)',
 stockValue:'Quanto valem os produtos e materiais guardados no local? (R$)',
 buildingValue:'Se souber, quanto custaria reconstruir o imóvel? (R$)',
 employees:'Quantas pessoas são empregadas neste local?',
 payroll:'Quanto é pago em salários por mês neste local? (R$)',
 monthlyExpenses:'Quanto a empresa gasta por mês para manter este local funcionando? (R$)',
 monthlyRevenue:'Quanto a empresa recebe, em média, por mês com vendas ou serviços? (R$)',
 units:'Quantos locais de funcionamento a empresa tem?',rentValue:'Quanto é o aluguel mensal deste local? (R$)'};
export function glassFields(field) {
 return field('glassCount','Quantos itens de vidro precisam de proteção?',{type:'number',required:false,min:'0',max:'1000000',increment:'1',inputmode:'numeric',help:'Conte janelas, portas de vidro, vitrines e espelhos. Uma quantidade aproximada já ajuda. Deixe em branco se não souber.'})+`<p class="catalog-note span-two">O valor para trocar os vidros pode ser confirmado depois com um especialista. A quantidade, sozinha, não informa esse custo.</p>`;
}
export function riskFields(state, questionnaire, field, {internal=false}={}) {
  return `<p class="quote-helper">${esc(questionnaire.notice)} Campos financeiros vazios aproveitam o cadastro vinculado; sem cadastro, ficam desconhecidos. Zero significa ausência confirmada.</p>
    <section class="risk-inventory"><h2>Valores do estabelecimento</h2><p>Equipamentos já fazem parte dos bens: informe apenas a parcela elétrica no segundo campo. Estoque fica separado. Os valores devem refletir reposição, sem somar os mesmos itens duas vezes.</p>
    <div class="form-grid">${field('cnae',internal?'CNAE principal (sete dígitos)':'Código da atividade no CNPJ (CNAE), se souber',{required:false,full:true,maxlength:10,help:'Se vincular uma empresa, deixe vazio para usar o CNAE cadastrado. O código da lista de atividades não é um CNAE.'})}
    ${NUMERIC_FIELDS.filter(([key])=>internal||key!=='glassValue').map(([key,label])=>field(key,internal?label:(CUSTOMER_LABELS[key]||label),{type:'number',required:false,min:'0',max:key==='employees'?'1000000':'1000000000000',inputmode:'decimal'})).join('')}${glassFields(field)}</div></section>
    <section class="risk-questions"><h2>Oito perguntas sobre a proteção</h2>${questionnaire.groups.map(group=>`<section class="risk-group"><h3>${esc(!internal&&group.code==='RESPONSABILIDADE_CIVIL_EMPREGADOR'?'Proteção dos funcionários':group.name)}</h3>${group.questions.map(q=>`<fieldset class="risk-question"><legend>${esc(q.text)}</legend>${[['yes','Sim'],['no','Não']].map(([value,label])=>`<label><input type="radio" name="${q.id}" value="${value}" required ${state[q.id]===value?'checked':''}> ${label}</label>`).join('')}</fieldset>`).join('')}</section>`).join('')}</section>`;
}

export function baseFields(context, state) {
  return `<details class="base-picker" ${state.sourceKey||context?'open':''}><summary>Usar cadastro existente do Datathon</summary><p>Selecione uma empresa e uma unidade para calcular o plano recomendado com seus bens, estoques e sinais financeiros. A análise e a explicação aparecem automaticamente abaixo. O endereço informado pode atualizar a referência municipal. Esta base local não é uma conexão bancária de produção.</p>${context ? `<div class="qfield"><label for="sourceKey">Empresa / estabelecimento</label><select id="sourceKey" name="sourceKey"><option value="">Continuar sem vínculo</option>${context.estabelecimentos.map(r=>`<option value="${esc(r.empresaId+'|'+r.imovelId)}" ${state.sourceKey===r.empresaId+'|'+r.imovelId?'selected':''}>${esc(r.label)}</option>`).join('')}</select></div><p>${context.estabelecimentos.length} estabelecimentos disponíveis. Ao vincular, confira a atividade escolhida e o CNAE cadastrado.</p>` : '<button type="button" class="btn btn-outline" id="load-base">Carregar base local</button><p id="base-status" role="status"></p>'}</details>`;
}

export function recommendationView(result) {
  if (!result) return '';
  const rec = result.recomendacao;
  return `<section class="recommendation" aria-label="Resultado calculado"><p class="result-eyebrow">Recomendação calculada · MVP integrado</p><h2>${rec.indicacao_bloqueada?'Triagem exige análise oficial':esc({ESSENCIAL:'Empresarial Essencial',PRATICO:'Empresarial Prático',TOTAL:'Empresarial Total'}[rec.plano_recomendado])}</h2>${result.vidrosDeclarados?.quantidade!=null?`<p>Vidros: aproximadamente ${esc(result.vidrosDeclarados.quantidade)} itens declarados. A quantidade não é convertida em valor de reposição.</p>`:''}<p>${esc(rec.justificativa)}</p><p>Confiança dos dados: <strong>${points(rec.confianca_geral*100)}%</strong> · Meta de aderência: ${points(rec.meta_aderencia)}%</p>
    ${personalizationView(result)}<div class="index-grid">${Object.entries(result.indices).map(([code,s])=>indexEvidence(code,s)).join('')}</div>
    ${assetEvidence(result.rastreabilidade)}<details class="result-details"><summary>Bens e origem dos dados</summary><dl><dt>Bens ponderados no local</dt><dd>${money(result.patrimonio.bens_ponderados)}</dd><dt>Equipamentos, já incluídos nos bens</dt><dd>${money(result.patrimonio.equipamentos_ponderados)}</dd><dt>Estoque separado</dt><dd>${money(result.patrimonio.estoque_medio_estimado)}</dd><dt>Reconstrução informada</dt><dd>${money(result.patrimonio.valor_predio_reposicao_brl)}</dd></dl><p>Cadastro vinculado: ${result.vinculoBase?'Sim':'Não'}. Bens cadastrados são ponderados uma única vez por probabilidade de vínculo. Valores confirmados no formulário substituem os agregados correspondentes.</p><ul>${Object.entries(result.origens).map(([k,v])=>`<li>${esc(ORIGIN_LABELS[k]||k)}: ${esc(v)}</li>`).join('')}</ul></details>
    <details class="result-details"><summary>Fontes públicas, períodos e pendências</summary><p>Município: ${esc(result.localizacao.municipio_real)} / ${esc(result.localizacao.uf_real)} · CNAE ${esc(result.atividade.cnaeUtilizado||'não informado')} · IBGE ${esc(result.localizacao.codigo_ibge_municipio||'não confirmado')}</p><p>Origem do vínculo municipal: ${esc(result.localizacao.fonte_localizacao||'Não disponível')}.</p>${result.fontes.map(f=>`<p><strong>${esc(f.tipo)}:</strong> ${f.disponivel?'Referência disponível':'Sem referência'} · ${esc(f.periodo||'Período não informado')}</p>${String(f.fonte||'').split(' | ').filter(Boolean).map(url=>/^https:\/\//.test(url)?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Consultar fonte de ${esc(f.tipo)} ↗</a>`:'').join('<br>')}<p>${esc(f.metodologia||'')}</p>`).join('')}<ul>${[...result.avisos,...rec.perguntas_confirmacao].map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details><p class="catalog-note">${esc(result.observacao)} A faixa indica sensibilidade à informação incompleta, sem interpretação estatística.</p></section>`;
}

export function cadastroRecommendationView(result) {
  if (!result) return '';
  const rec=result.recomendacao, data=result.dadosCadastrais;
  const planName=p=>({ESSENCIAL:'Essencial',PRATICO:'Prático',TOTAL:'Total'}[p]||p);
  const decimal=n=>Number(n).toLocaleString('pt-BR',{maximumFractionDigits:3});
  const fact=(value)=>value==null?'Não informado':typeof value==='object'?JSON.stringify(value):String(value);
  const fields=[['bens_quantidade','Quantidade de bens cadastrados',false],['bens_total_referencia','Valor cadastrado dos bens',true],
    ['bens_ponderados','Valor dos bens atribuído à unidade',true],['estoque_medio_estimado','Estoque médio',true],
    ['estoque_pico_estimado','Estoque de pico (cenário alternativo)',true],['quantidade_unidades','Unidades da empresa',false],
    ['quantidade_funcionarios_estimada','Empregados estimados na empresa',false],['folha_pagamento_mensal','Folha mensal desta unidade',true],
    ['despesa_fixa_mensal_estimada','Despesas fixas mensais da unidade',true],['faturamento_mensal','Faturamento mensal da empresa',true],
    ['valor_aluguel_recorrente','Aluguel mensal',true],['material_parede_externa_cadastrado','Material das paredes',false],
    ['padrao_construtivo_cadastrado','Padrão construtivo',false]];
  return `<section class="cadastro-analysis" aria-label="Análise inicial do cadastro"><h2>Análise inicial do cadastro</h2>
    <p class="quote-helper">${esc(result.cadastro.empresa_id)} / ${esc(result.cadastro.imovel_id)} · ${esc(result.localizacao.municipio_real)} / ${esc(result.localizacao.uf_real)}. Calculada com os dados já disponíveis. Nenhuma resposta do questionário foi presumida; as próximas etapas permitem refinar esta indicação.</p>
    ${recommendationView(result)}
    <section class="decision-explanation"><h2>Como chegamos a essa indicação</h2>
    <h3>1. Dados usados neste estabelecimento</h3><p>Atividade cadastrada: ${esc(result.cadastro.descricao_cnae||result.cadastro.grupo_atividade||'Não informada')}. CNAE: ${esc(result.atividade.cnaeUtilizado||'Não informado')}.</p>
    <dl class="audit-facts">${fields.map(([key,label,currency])=>`<dt>${esc(label)}</dt><dd>${currency?money(data[key]):esc(fact(data[key]))}</dd>`).join('')}</dl>
    <p>Somamos valor cadastrado × probabilidade de vínculo para cada bem. Equipamentos já estão nesse total. O estoque médio entra separadamente; o pico participa de outro cenário. Faturamento empresarial não é dividido arbitrariamente entre filiais.</p>
    <h3>2. Cálculo dos quatro índices</h3><p>R representa exposição ao evento; I, impacto; V, vulnerabilidade. São componentes de 0 a 1. As notas finais vão de 0 a 100 e não representam probabilidade de sinistro. Componentes sem informação mantêm incerteza explícita.</p>
    ${Object.values(result.indices).map(s=>`<article class="audit-index"><h4>${esc(s.nome)}: ${points(s.prioridade)} / 100</h4><p>${esc(s.justificativa)}</p><p>R = ${decimal(s.risco_evento_relativo)}; I = ${decimal(s.impacto_normalizado)}; V = ${decimal(s.vulnerabilidade)}. Valor exposto no cenário: ${money(s.valor_exposto_brl)}.</p><p><strong>Memória de cálculo:</strong> ${decimal(s.decomposicao.base_pontos)} pontos de base + ${decimal(s.decomposicao.interacao_pontos)} de interação, com limite de 100.</p><p><code>${esc(s.formula)}</code></p><p>Parâmetros desta conta: p = ${decimal(s.decomposicao.piso_impacto)}; a = ${decimal(s.decomposicao.piso_evento)}; b = ${decimal(s.decomposicao.piso_vulnerabilidade)}; k = ${decimal(s.decomposicao.coeficiente_interacao)}; D = ${decimal(s.decomposicao.dependencia_interacao)}. A soma é limitada ao intervalo de 0 a 100.</p>
    <ul>${s.fatores_evento.map(f=>`<li><strong>${esc(f.nome)}</strong>: dado ${esc(fact(f.valor_original))}; normalizado ${decimal(f.valor_normalizado)}; peso ${decimal(f.peso_evento)}. ${esc(f.transformacao)}. ${esc(f.observacao)}</li>`).join('')}<li><strong>Impacto:</strong> ${esc(s.fator_impacto.transformacao)}. ${esc(s.fator_impacto.observacao)}</li><li><strong>Vulnerabilidade:</strong> ${esc(s.fator_vulnerabilidade.transformacao)}. ${esc(s.fator_vulnerabilidade.observacao)}</li></ul></article>`).join('')}
    <h3>3. Participação das dez necessidades</h3><p>Os quatro índices acima se juntam às seis preferências das coberturas comuns. Para cada cobertura, multiplicamos sua prioridade pelo peso configurado. A soma é ${decimal(rec.comparacao[0].pontos_totais)} pontos ponderados.</p>
    <div class="audit-table-wrap"><table class="audit-table"><caption>Necessidades calculadas e coberturas de cada plano</caption><thead><tr><th scope="col">Cobertura</th><th scope="col">Prioridade</th><th scope="col">Peso</th><th scope="col">Pontos</th>${rec.comparacao.map(p=>`<th scope="col">${planName(p.plano)}</th>`).join('')}</tr></thead><tbody>${Object.entries(rec.necessidades).map(([code,n])=>`<tr><th scope="row">${esc(n.nome)}<small>${n.origem==='INDICE_MULTIFATORIAL'?'Índice multifatorial':'Preferência heurística'}</small></th><td>${decimal(n.prioridade)}</td><td>${decimal(n.peso)}</td><td>${decimal(n.prioridade*n.peso)}</td>${rec.comparacao.map(p=>`<td>${p.coberturas.includes(code)?'Incluída':'Ausente'}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
    <h3>4. Por que este plano foi escolhido</h3><p>Aderência = pontos das necessidades cobertas ÷ pontos de todas as necessidades × 100. Escolhemos o primeiro nível que alcança ${decimal(rec.meta_aderencia)}% e contém as coberturas indispensáveis, incluindo índices prioritários de 70 ou mais. Preço não é usado na decisão, pois não temos cotação individual.</p>
    <div class="audit-table-wrap"><table class="audit-table"><caption>Comparação calculada dos planos</caption><thead><tr><th scope="col">Plano</th><th scope="col">Pontos atendidos / total</th><th scope="col">Aderência</th><th scope="col">Decisão</th></tr></thead><tbody>${rec.comparacao.map(p=>`<tr ${p.plano===rec.plano_recomendado?'class="chosen-plan"':''}><th scope="row">${planName(p.plano)}</th><td>${decimal(p.pontos_atendidos)} / ${decimal(p.pontos_totais)}</td><td>${decimal(p.aderencia_percentual)}%</td><td>${p.plano===rec.plano_recomendado?'Recomendado: primeiro nível que atende aos critérios':!p.atinge_meta?'Abaixo da meta':p.indispensaveis_ausentes.length?'Faltam coberturas indispensáveis':'Atende, mas o nível anterior já é suficiente'}</td></tr>`).join('')}</tbody></table></div>
    <p>${rec.recomendacao_estavel?'A indicação permanece a mesma nos cenários de sensibilidade calculados.':`Com a incerteza dos dados, o plano pode variar entre ${esc(planName(rec.plano_cenario_inferior))} e ${esc(planName(rec.plano_cenario_superior))}. As confirmações do formulário ajudam a refinar a análise.`} Os cálculos usam valores sem arredondamento; a tela arredonda apenas a apresentação.</p>
    <h3>5. O que ainda precisa ser confirmado</h3><ul>${[...result.avisos,...rec.perguntas_confirmacao].map(x=>`<li>${esc(x)}</li>`).join('')}</ul>
    <p>As fontes públicas, períodos, confiança e limitações estão disponíveis no bloco da recomendação acima.</p></section></section>`;
}
