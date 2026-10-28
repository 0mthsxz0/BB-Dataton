const esc = x => String(x ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const decimal = (x,digits=4) => Number(x).toLocaleString('pt-BR',{maximumFractionDigits:digits});
const money = x => Number(x).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const STATES = {AUSENTE:'Não disponível',EXCLUIDO_ESCOPO:'Excluído pelo escopo',DECLARADO:'Declarado no formulário',CADASTRO_ESTIMATIVA:'Cadastro / estimativa',HIPOTESE_MODELO:'Hipótese do modelo'};
const QUALITY_STATES = {INDISPONIVEL:'Dados indisponíveis',INCOMPATIVEL:'Dados incompatíveis',DESATUALIZADO:'Base desatualizada',PERIODO_INVALIDO:'Período inadequado',INTEGRIDADE_NAO_VERIFICADA:'Integridade não verificada',METADADOS_INSUFICIENTES:'Origem incompleta',COBERTURA_INSUFICIENTE:'Cobertura insuficiente',INCONSISTENTE:'Dados inconsistentes',LOCALIZACAO_INVALIDA:'Localização não validada',EXPERIMENTAL:'Referência experimental',SIMULACAO:'Simulação'};
const LABELS = {
  taxa_furto_domicilios:'Domicílios com vítimas de furto / domicílios',taxa_roubo_domicilios:'Domicílios com vítimas de roubo / domicílios',
  exposicao_bruta:'Média das taxas domiciliares',seguranca_da_cidade_0_1:'Segurança municipal relativa (0–1)',confianca_seguranca_0_1:'Confiança contextual da referência (0–1)',
  roubo_comercio_total:'Roubos em comércio no período',estabelecimentos_referencia:'Estabelecimentos no denominador',taxa_por_mil_estabelecimentos:'Ocorrências por mil estabelecimentos',referencia_taxa_por_mil:'Referência de normalização por mil',regioes_fonte:'Regiões que compõem a referência',atualizado_em_utc:'Data de preparação da referência',
  fonte_denominador:'Fonte dos estabelecimentos',ano_denominador:'Ano dos estabelecimentos',meses_observados_seguranca:'Meses observados',integridade_seguranca:'Conferência do hash do arquivo',
  frequencia_rajada_forte:'Dias com rajada ≥50 km/h / dias válidos',frequencia_rajada_severa:'Dias com rajada ≥70 km/h / dias válidos',frequencia_vento_chuva:'Dias com vento ≥40 km/h e chuva ≥50 mm / dias conjuntos válidos',
  exposicao_climatica_bruta:'Frequência climática ponderada',exposicao_climatica_0_1:'Exposição climática normalizada (0–1)',dias_esperados:'Dias esperados na série',dias_vento_validos:'Dias com vento válido',dias_conjuntos_validos:'Dias com vento e chuva válidos',modelo_clima:'Modelo climático',
  grau_risco_nr4:'Grau ocupacional NR-4',descricao_nr4:'Descrição da classe CNAE na NR-4',pagina:'Página do documento oficial',
  bens_ponderados:'Bens atribuídos à unidade',bens_total_referencia:'Bens de referência sem ponderação',estoque_medio:'Estoque médio',estoque_pico:'Estoque de pico',valor_predio_reposicao_brl:'Reconstrução sem terreno',
  equipamentos_ponderados:'Equipamentos atribuídos à unidade',equipamentos_total_referencia:'Equipamentos de referência',valor_mensal:'Valor mensal usado',meses_paralisacao_min:'Meses no cenário mínimo',meses_paralisacao_max:'Meses no cenário máximo',
  folha_pagamento_mensal:'Folha mensal da unidade',funcionarios_empresa:'Empregados estimados na empresa',valor_vidros_reposicao_brl:'Reposição de vidros',
  securityControls:'Alarme monitorado e controle de acesso',portableGoods:'Bens de fácil transporte e revenda',roofMaintained:'Telhado inspecionado e conservado',exposedAssets:'Bens externos expostos',hasEmployees:'Há empregados na unidade',hazardousWork:'Há tarefas com exposição física',hasGlass:'Há vidros a proteger',glassExposed:'Vidros expostos a impactos',
  territorio:'Referência territorial original',grau_nr4:'Grau NR-4', financeira:'Componente financeiro',construtiva:'Componente construtivo', componente_mvp:'Componente original do motor',
  piso_impacto:'Piso do impacto',piso_evento:'Piso do evento',piso_vulnerabilidade:'Piso de vulnerabilidade',coeficiente_interacao:'Coeficiente de interação',dependencia_interacao:'Dependência na interação',
};
const ratios = new Set(['taxa_furto_domicilios','taxa_roubo_domicilios','frequencia_rajada_forte','frequencia_rajada_severa','frequencia_vento_chuva']);
const brl = /^(bens_|estoque_|equipamentos_|valor_mensal$|valor_predio|valor_vidros|folha_pagamento|despesa_fixa|despesas_unidade|receita_empresa|informatica_ponderada)/;
function value(x,unit,key=''){
  if(x==null)return 'Não disponível';
  if(typeof x==='boolean')return x?'Sim':'Não';
  if(typeof x==='number'){
    if(unit==='BRL')return money(x);
    if(unit==='percentual')return decimal(x)+'%';
    if(ratios.has(key))return `${decimal(x*100)}% <small>valor bruto: ${esc(x)}</small>`;
    return decimal(x,6);
  }
  return esc(x);
}
function dataTree(data){
  if(data==null)return 'Não disponível';
  if(Array.isArray(data))return data.map(x=>dataTree(x)).join('; ');
  if(typeof data!=='object')return value(data);
  return `<dl class="calculation-data">${Object.entries(data).map(([k,v])=>`<dt>${esc(LABELS[k]||k)}</dt><dd>${v&&typeof v==='object'?dataTree(v):value(v,brl.test(k)?'BRL':null,k)}</dd>`).join('')}</dl>`;
}
function origin(e){
  return `${esc(e.origem)}${e.arquivo?` · <code>${esc(e.arquivo)}</code>`:''} · <code>${(e.campos_origem||[e.campo]).map(esc).join(' + ')}</code>${e.transformacao_origem?`<br>${esc(e.transformacao_origem)} → <code>${esc(e.campo)}</code>`:''}${e.chave?` · ${Object.values(e.chave).map(esc).join(' / ')}`:''}`;
}
export function evidenceRows(rows=[]){
  return `<div class="audit-table-wrap"><table class="audit-table evidence-table"><caption>Dados de cálculo e contexto, com sua procedência</caption><thead><tr><th>Dado</th><th>Valor utilizado</th><th>Origem e estado</th></tr></thead><tbody>${rows.map(e=>`<tr><th scope="row">${esc(e.rotulo)}</th><td>${value(e.valor,e.unidade)}</td><td>${origin(e)}<br><strong>${esc(STATES[e.estado]||e.estado)}</strong>. ${esc(e.confirmar)}</td></tr>`).join('')}</tbody></table></div>`;
}
export function dimensionEvidence(d){
  return `<p>${esc(d.justificativa)}</p><ul class="dimension-evidence">${(d.evidencias||[]).map(e=>`<li><strong>${esc(e.rotulo)}: ${value(e.valor,e.unidade)}</strong><br>${origin(e)}<br>${esc(STATES[e.estado]||e.estado)}.</li>`).join('')}</ul>
    <details><summary>Dados usados na conta desta faixa</summary>${dataTree(d.dados_calculo)}<p>${esc(d.formula)}</p><ul>${(d.confirmar||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details><p>Confiança contextual: ${decimal(d.confianca*100,1)}%.</p>`;
}
function publicEvidence(p){
  if(!p)return '<p class="source-note">Sem API externa específica integrada para este índice. Os sinais utilizados abaixo são cadastrais, declarados ou hipóteses do modelo.</p>';
  const links=String(p.fonte||'').split(' | ').filter(url=>/^https:\/\//.test(url));
  const m=p.parametros||{};
  const labels={...LABELS,frequencia_rajada_forte:`Dias com rajada ≥${m.rajada_forte_kmh??'limiar não disponível'} km/h / dias válidos`,frequencia_rajada_severa:`Dias com rajada ≥${m.rajada_severa_kmh??'limiar não disponível'} km/h / dias válidos`,frequencia_vento_chuva:`Dias com vento ≥${m.rajada_chuva_kmh??'limiar não disponível'} km/h e chuva ≥${m.chuva_mm??'limiar não disponível'} mm / dias conjuntos válidos`};
  return `<section class="public-evidence"><h4>Referência pública e dados disponíveis</h4><p>${esc(p.modo_acesso)}</p><p><strong>${esc(p.condicao||'')}</strong></p><p><strong>Período:</strong> ${esc(p.periodo||'Não disponível')} · <strong>Abrangência:</strong> ${esc(p.granularidade||'Não disponível')}.</p><p>${Object.entries(p.vinculo||{}).map(([k,v])=>`${esc(k)}: ${esc(v??'Não disponível')}`).join(' · ')}</p>
    ${links.length?links.map(url=>`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Consultar fonte oficial ↗</a>`).join(' · '):'<p>Sem fonte externa vinculada disponível para esta unidade.</p>'}
    <div class="audit-table-wrap"><table class="audit-table"><caption>Valores da referência armazenada (não são uma consulta ao vivo)</caption><thead><tr><th>Indicador / dado</th><th>Valor da fonte</th></tr></thead><tbody>${Object.entries(p.dados).filter(([k])=>!k.startsWith('sha256')).map(([k,v])=>`<tr><th scope="row">${esc(labels[k]||k)}<small><code>${esc(k)}</code></small></th><td>${value(v,null,k)}</td></tr>`).join('')}</tbody></table></div>
    ${p.metodologia?`<details><summary>Metodologia da referência</summary><p>${esc(p.metodologia)}</p></details>`:''}<details><summary>Arquivo e integridade da referência</summary><p><code>${esc(p.arquivo)}</code> · SHA-256 do snapshot: <code>${esc(p.sha256_snapshot||'Não disponível')}</code></p>${Object.entries(p.dados).filter(([k])=>k.startsWith('sha256')).map(([k,v])=>`<p>${esc(k)}: <code>${esc(v||'Não disponível')}</code></p>`).join('')}</details></section>`;
}
export function indexEvidence(code,s){
  return `<article class="index-card report-index" data-index-code="${esc(code)}"><header><h3>${esc(s.nome)}</h3><p><strong>${decimal(s.prioridade,1)}</strong> / 100 · ${esc(s.classe)}</p><progress max="100" value="${s.prioridade}" aria-label="${esc(s.nome)}: ${decimal(s.prioridade,1)} de 100"></progress><small>Sensibilidade ${decimal(s.prioridade_min,1)}–${decimal(s.prioridade_max,1)} · Confiança ${decimal(s.confianca*100,1)}%</small></header>
    ${s.qualidade_seguranca?`<aside role="note"><strong>Base territorial: ${esc(QUALITY_STATES[s.qualidade_seguranca.status]||s.qualidade_seguranca.status)}</strong><p>${(s.qualidade_seguranca.motivos||[]).map(esc).join(' ')}</p><p>Avaliação em ${esc(s.qualidade_seguranca.data_analise)} · Política ${esc(s.qualidade_seguranca.politica)}. A confiança exibida é um peso do modelo; não é precisão estatística.</p></aside>`:''}
    <h4>O que essa pontuação significa para esta unidade</h4><p class="context-reading">${esc(s.leitura_contextual||s.justificativa)}</p><p>${esc(s.explicacao_contextual||'')}</p><p>O cenário usa ${s.valor_exposto_brl==null?'impacto financeiro ainda desconhecido':money(s.valor_exposto_brl)} como exposição contextual; o impacto normalizado efetivo é ${decimal(s.impacto_normalizado,6)}. A nota ${decimal(s.prioridade,1)} expressa prioridade de proteção, sem estimar chance de sinistro.</p>
    ${publicEvidence(s.referencia_publica)}<details class="local-evidence" open><summary>Dados da empresa e declarações que contextualizam este índice</summary>${evidenceRows(s.evidencias)}<h4>Respostas consideradas</h4>${dataTree(s.respostas_utilizadas)}<p>“Não disponível” significa que a resposta não foi presumida.</p></details>
    <details class="technical-evidence"><summary>Memória técnica: fatores, pesos e cálculo</summary><p>${esc(s.justificativa)}</p><p>R = ${decimal(s.risco_evento_relativo,6)} · I = ${decimal(s.impacto_normalizado,6)} · V = ${decimal(s.vulnerabilidade,6)}.</p><p>Base ${decimal(s.decomposicao.base_pontos)} + interação ${decimal(s.decomposicao.interacao_pontos)} + ajuste do limite ${decimal(s.decomposicao.efeito_limite_pontos)} = ${decimal(s.prioridade)} pontos.</p><p><code>${esc(s.formula)}</code></p>
    ${s.fatores_evento.map(f=>`<section class="factor-evidence"><h4>${esc(f.nome)}</h4>${dataTree(f.valor_original)}<p>Normalizado: ${decimal(f.valor_normalizado,6)} · Peso no evento: ${decimal(f.peso_evento,6)} · Contribuição: ${decimal(f.contribuicao_evento,6)}. Confiança: ${decimal(f.confianca*100,1)}%.</p><p>${esc(f.transformacao)}. ${esc(f.observacao)}</p></section>`).join('')}
    <h4>Dados e transformação do impacto</h4>${dataTree(s.fator_impacto.valor_original)}<p>${esc(s.fator_impacto.transformacao)}. ${esc(s.fator_impacto.observacao)}</p><h4>Vulnerabilidade</h4>${dataTree(s.fator_vulnerabilidade.valor_original)}<p>${esc(s.fator_vulnerabilidade.transformacao)}. ${esc(s.fator_vulnerabilidade.observacao)}</p></details></article>`;
}
export function assetEvidence(trace){
  if(!trace)return '';
  return `<details class="result-details asset-evidence"><summary>Rastrear bens: registros, valores e ponderação</summary><p>${esc(trace.formula_bens)}</p><p>${esc(trace.observacao)}</p><p>${trace.bens_cadastrais_utilizados?'O agregado cadastral foi utilizado neste cenário.':'Os registros abaixo são referência cadastral; o agregado foi substituído, excluído pelo escopo ou não está disponível. Não será somado novamente.'}</p>
    ${trace.bens.length?`<div class="audit-table-wrap"><table class="audit-table"><caption>Bens vinculados somente à empresa e unidade selecionadas</caption><thead><tr><th>Bem / tipo</th><th>Valor cadastrado</th><th>Probabilidade de vínculo</th><th>Valor × vínculo</th><th>Confiança do vínculo</th></tr></thead><tbody>${trace.bens.map(b=>`<tr><th scope="row">${esc(b.bem_id)}<small>${esc(b.tipo_bem)}</small></th><td>${value(b.valor_cadastrado,'BRL')}</td><td>${value(b.probabilidade_vinculo)}</td><td>${value(b.valor_ponderado,'BRL')}</td><td>${esc(b.confianca_vinculo||'Não disponível')}</td></tr>`).join('')}</tbody></table></div>`:'<p>Sem registros de bens vinculados disponíveis para esta simulação.</p>'}<p>Fonte: <code>${esc(trace.arquivo_bens)}</code> · ${Object.values(trace.vinculo).filter(Boolean).map(esc).join(' / ')}.</p><p>SHA-256: <code>${esc(trace.sha256_bens||'Não disponível')}</code></p></details>`;
}
