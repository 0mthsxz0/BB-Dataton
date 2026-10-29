const esc = x => String(x ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const decimal = (x,digits=4) => Number(x).toLocaleString('pt-BR',{maximumFractionDigits:digits});
const money = x => Number(x).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const STATES = {AUSENTE:'Não disponível',EXCLUIDO_ESCOPO:'Excluído pelo escopo',DECLARADO:'Declarado no formulário',CADASTRO_ESTIMATIVA:'Cadastro / estimativa',PERFIL_ATIVIDADE_ESTIMATIVA:'Referência agregada da atividade',HIPOTESE_MODELO:'Hipótese do modelo'};
const QUALITY_STATES = {INDISPONIVEL:'Dados indisponíveis',INCOMPATIVEL:'Dados incompatíveis',DESATUALIZADO:'Base desatualizada',PERIODO_INVALIDO:'Período inadequado',INTEGRIDADE_NAO_VERIFICADA:'Integridade não verificada',METADADOS_INSUFICIENTES:'Origem incompleta',COBERTURA_INSUFICIENTE:'Cobertura insuficiente',INCONSISTENTE:'Dados inconsistentes',LOCALIZACAO_INVALIDA:'Localização não validada',EXPERIMENTAL:'Referência experimental',SIMULACAO:'Simulação'};
const LABELS = {
  taxa_furto_domicilios:'Domicílios com vítimas de furto / domicílios',taxa_roubo_domicilios:'Domicílios com vítimas de roubo / domicílios',
  exposicao_bruta:'Média das taxas domiciliares',seguranca_da_cidade_0_1:'Segurança municipal relativa (%)',confianca_seguranca_0_1:'Confiança contextual da referência (%)',
  roubo_comercio_total:'Roubos em comércio no período',estabelecimentos_referencia:'Estabelecimentos no denominador',taxa_por_mil_estabelecimentos:'Ocorrências / estabelecimentos (%)',referencia_taxa_por_mil:'Referência de normalização (%)',regioes_fonte:'Regiões que compõem a referência',atualizado_em_utc:'Data de preparação da referência',
  fonte_denominador:'Fonte dos estabelecimentos',ano_denominador:'Ano dos estabelecimentos',meses_observados_seguranca:'Meses observados',integridade_seguranca:'Conferência do hash do arquivo',
  frequencia_rajada_forte:'Dias com rajada ≥50 km/h / dias válidos',frequencia_rajada_severa:'Dias com rajada ≥70 km/h / dias válidos',frequencia_vento_chuva:'Dias com vento ≥40 km/h e chuva ≥50 mm / dias conjuntos válidos',
  exposicao_climatica_bruta:'Frequência climática ponderada',exposicao_climatica_0_1:'Exposição climática normalizada (%)',dias_esperados:'Dias esperados na série',dias_vento_validos:'Dias com vento válido',dias_conjuntos_validos:'Dias com vento e chuva válidos',modelo_clima:'Modelo climático',
  grau_risco_nr4:'Grau ocupacional NR-4',descricao_nr4:'Descrição da classe CNAE na NR-4',pagina:'Página do documento oficial',
  bens_ponderados:'Bens atribuídos à unidade',bens_total_referencia:'Bens de referência sem ponderação',estoque_medio:'Estoque médio',estoque_pico:'Estoque de pico',valor_predio_reposicao_brl:'Reconstrução sem terreno',
  equipamentos_ponderados:'Equipamentos atribuídos à unidade',equipamentos_total_referencia:'Equipamentos de referência',valor_mensal:'Valor mensal usado',meses_paralisacao_min:'Meses no cenário mínimo',meses_paralisacao_max:'Meses no cenário máximo',
  folha_pagamento_mensal:'Folha mensal da unidade',funcionarios_empresa:'Empregados estimados na empresa',valor_vidros_reposicao_brl:'Reposição de vidros',
  securityControls:'Alarme monitorado e controle de acesso',portableGoods:'Bens de fácil transporte e revenda',roofMaintained:'Telhado inspecionado e conservado',exposedAssets:'Bens externos expostos',hasEmployees:'Há empregados na unidade',hazardousWork:'Há tarefas com exposição física',hasGlass:'Há vidros a proteger',glassExposed:'Vidros expostos a impactos',
  territorio:'Referência territorial original',grau_nr4:'Grau NR-4', financeira:'Componente financeiro',construtiva:'Componente construtivo', componente_mvp:'Componente original do motor',
  piso_impacto:'Piso do impacto',piso_evento:'Piso do evento',piso_vulnerabilidade:'Piso de vulnerabilidade',coeficiente_interacao:'Coeficiente de interação',dependencia_interacao:'Dependência na interação',
};
const ratios = new Set(['taxa_furto_domicilios','taxa_roubo_domicilios','exposicao_bruta','seguranca_da_cidade_0_1','confianca_seguranca_0_1','frequencia_rajada_forte','frequencia_rajada_severa','frequencia_vento_chuva','exposicao_climatica_bruta','exposicao_climatica_0_1','probabilidade_vinculo','probabilidade_bem_no_imovel_referencia','financeira','construtiva','componente_mvp','piso_impacto','piso_evento','piso_vulnerabilidade','coeficiente_interacao','dependencia_interacao','territorio']);
const MEANINGS = {
  taxa_furto_domicilios:'Parcela de domicílios com vítimas de furto no período; não mede furto em empresas.',
  taxa_roubo_domicilios:'Parcela de domicílios com vítimas de roubo no período; não mede roubo em empresas.',
  exposicao_bruta:'Média das taxas domiciliares armazenadas, antes da normalização.',
  seguranca_da_cidade_0_1:'Índice relativo de segurança: 100% é o extremo de maior segurança da escala do modelo; não significa ausência de crime.',
  confianca_seguranca_0_1:'Peso de confiança atribuído à referência pelo modelo; não é precisão estatística.',
  roubo_comercio_total:'Quantidade de ocorrências registradas no período e território da referência.',
  estabelecimentos_referencia:'Quantidade de estabelecimentos usada como denominador da taxa.',
  taxa_por_mil_estabelecimentos:'Ocorrências divididas pelos estabelecimentos, apresentadas em porcentagem. A fonte armazena a taxa por mil: dividimos por 10. Não é probabilidade individual e pode superar 100%.',
  referencia_taxa_por_mil:'Escala de comparação usada na normalização, convertida de por mil para porcentagem (÷ 10).',
  regioes_fonte:'Regiões cujos registros compõem o indicador territorial.',
  atualizado_em_utc:'Data de preparação do arquivo local, não de consulta em tempo real.',
  fonte_denominador:'Origem da contagem dos estabelecimentos usada no denominador.',
  ano_denominador:'Ano a que se refere a contagem dos estabelecimentos.',
  meses_observados_seguranca:'Quantidade de meses com dados disponíveis no período.',
  integridade_seguranca:'Resultado da conferência do arquivo; não valida a atualidade ou a adequação estatística.',
  frequencia_rajada_forte:'Porcentagem dos dias válidos com rajadas acima do limiar indicado.',
  frequencia_rajada_severa:'Porcentagem dos dias válidos com rajadas severas acima do limiar indicado.',
  frequencia_vento_chuva:'Porcentagem dos dias com medições conjuntas que atingiram os limiares de vento e chuva.',
  exposicao_climatica_bruta:'Combinação ponderada das frequências históricas de vento e chuva.',
  exposicao_climatica_0_1:'Índice climático normalizado: 100% é o extremo superior da escala do modelo, não certeza de vendaval.',
  dias_esperados:'Total de dias previstos para o período histórico analisado.',
  dias_vento_validos:'Dias com medições válidas de vento na série.',
  dias_conjuntos_validos:'Dias com medições válidas de vento e chuva simultaneamente.',
  modelo_clima:'Modelo de reanálise usado para reconstruir o histórico meteorológico.',
  grau_risco_nr4:'Classe ordinal oficial de 1 a 4. O modelo atribui um peso percentual à classe; o grau original não é uma porcentagem de acidentes.',
  descricao_nr4:'Descrição da atividade na classificação ocupacional consultada.',
  pagina:'Página do documento em que a classificação foi encontrada.',
};
const brl = /^(bens_|estoque_|equipamentos_|valor_mensal$|valor_predio|valor_vidros|folha_pagamento|despesa_fixa|despesas_unidade|receita_empresa|informatica_ponderada|energia_media_mensal)/;
export const percentage = (x,digits=2) => x==null||!Number.isFinite(Number(x))?'Não disponível':`${decimal(Number(x)*100,digits)}%`;
export function evidenceValue(x,unit,key=''){
  if(x==null||x==='')return 'Não disponível';
  const isPercentage=unit==='percentual'||key.endsWith('_pct')||key.startsWith('percentual_');
  const isRatio=unit==='proporcao'||ratios.has(key)||key.endsWith('_0_1')||key.startsWith('probabilidade_');
  const perThousand=['taxa_por_mil_estabelecimentos','referencia_taxa_por_mil'].includes(key);
  if(typeof x==='string'&&(unit==='BRL'||isPercentage||isRatio||perThousand)&&Number.isFinite(Number(x)))x=Number(x);
  if(typeof x==='boolean')return x?'Sim':'Não';
  if(typeof x==='number'){
    if(unit==='BRL')return money(x);
    if(isPercentage)return decimal(x)+'%';
    if(isRatio)return percentage(x,4);
    if(perThousand)return decimal(x/10,4)+'%';
    return decimal(x,6);
  }
  return esc(x);
}
const value=evidenceValue;
export function dataTree(data,key=''){
  if(data==null)return 'Não disponível';
  if(Array.isArray(data))return data.map(x=>dataTree(x,key)).join('; ');
  if(typeof data!=='object')return value(data,brl.test(key)?'BRL':null,key);
  return `<dl class="calculation-data">${Object.entries(data).map(([k,v])=>`<dt>${esc(LABELS[k]||k)}</dt><dd>${v&&typeof v==='object'?dataTree(v):value(v,brl.test(k)?'BRL':null,k)}</dd>`).join('')}</dl>`;
}
function rawCell(cell){
  const raw=cell.valor_original;
  const empty=raw==null||String(raw).trim()==='';
  const numeric=!empty&&cell.unidade!=='texto'&&Number.isFinite(Number(raw));
  return `<strong>${empty?'Célula vazia':value(numeric?Number(raw):raw,cell.unidade,cell.campo)}</strong><small class="source-raw">Conteúdo original da célula: <code>${empty?'(vazia)':esc(raw)}</code></small><p class="source-meaning">${esc(cell.significado)}</p>`;
}
function sourceValues(e){
  const rows=e.fontes_originais||[],p=e.perfil_referencia;
  if(p)return `<div class="source-values"><strong>Valor da fonte: ${value(e.valor,e.unidade,e.campo)}</strong><p class="source-meaning">${esc(e.significado)}</p><p>Referência agregada da atividade ${esc(p.cnae)} · ${esc(p.amostra?.empresas)} empresas / ${esc(p.amostra?.estabelecimentos)} estabelecimentos.</p>${p.campo_agregado?`<p>Campo agregado: <code>${esc(p.campo_agregado)}</code>.</p>`:''}<p>${esc(p.metodo)} ${esc(p.origem)}</p><p>Este valor resulta de uma agregação; não corresponde a uma célula de uma empresa identificada.</p></div>`;
  if(!rows.length)return `<p class="source-note">${e.estado==='DECLARADO'?'Valor fornecido no formulário; não há célula de planilha usada como fonte.':'Sem célula de origem disponível para este campo nos arquivos consultados.'}</p>`;
  return `<details class="source-values"><summary>Valores originais da fonte · ${rows.length} ${rows.length===1?'registro':'registros'}</summary><p>${e.fonte_utilizada?'Registros de origem; os avisos identificam eventuais linhas desconsideradas.':'Referência armazenada para comparação; estas células não foram usadas no valor atual.'} Linha da tabela contada com o cabeçalho na linha 1.</p><div class="audit-table-wrap"><table class="audit-table source-cells"><caption>Células originais do cadastro</caption><thead><tr><th>Arquivo / linha / registro</th><th>Campo</th><th>Valor da fonte e significado</th></tr></thead><tbody>${rows.flatMap(r=>r.celulas.map(c=>`<tr><td><code>${esc(r.arquivo)}</code><br>Linha ${esc(r.linha_tabela)} · ${esc(r.registro)}${r.observacao?`<p class="source-note">${esc(r.observacao)}</p>`:''}</td><th scope="row"><code>${esc(c.campo)}</code></th><td>${rawCell(c)}</td></tr>`)).join('')}</tbody></table></div></details>`;
}
function confirmation(e){
  const c=e.confirmacao;
  if(!c)return `<p class="evidence-confirmation">${esc(e.confirmar||'Confirme a informação com o responsável pelo estabelecimento.')}</p>`;
  return `<div class="evidence-confirmation"><strong>${e.estado==='EXCLUIDO_ESCOPO'?'Fora do escopo':'A confirmar — por quê?'}</strong><p>${esc(c.motivo)}</p>${c.pendencias?.length?`<strong>O que falta confirmar</strong><ul>${c.pendencias.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}<p><strong>Onde encontrar:</strong> ${esc(c.onde_encontrar)}</p></div>`;
}
function origin(e){
  return `${esc(e.origem)}${e.arquivo?` · <code>${esc(e.arquivo)}</code>`:''} · <code>${(e.campos_origem||[e.campo]).map(esc).join(' + ')}</code>${e.transformacao_origem?`<br>${esc(e.transformacao_origem)} → <code>${esc(e.campo)}</code>`:''}${e.chave?` · ${Object.values(e.chave).map(esc).join(' / ')}`:''}`;
}
export function evidenceRows(rows=[]){
  return `<div class="audit-table-wrap"><table class="audit-table evidence-table"><caption>Dados de cálculo e contexto, com sua procedência</caption><thead><tr><th>Dado</th><th>Valor utilizado</th><th>Origem e confirmação</th></tr></thead><tbody>${rows.map(e=>`<tr><th scope="row">${esc(e.rotulo)}</th><td>${value(e.valor,e.unidade,e.campo)}<p class="source-meaning">${esc(e.significado)}</p></td><td>${origin(e)}<br><strong>${esc(STATES[e.estado]||e.estado)}</strong>${sourceValues(e)}${confirmation(e)}</td></tr>`).join('')}</tbody></table></div>`;
}
export function dimensionEvidence(d){
  return `<p>${esc(d.justificativa)}</p><ul class="dimension-evidence">${(d.evidencias||[]).map(e=>`<li><strong>${esc(e.rotulo)}: ${value(e.valor,e.unidade,e.campo)}</strong><p class="source-meaning">${esc(e.significado)}</p>${origin(e)}<br>${esc(STATES[e.estado]||e.estado)}.${sourceValues(e)}${confirmation(e)}</li>`).join('')}</ul>
    <details><summary>Dados usados na conta desta faixa</summary>${dataTree(d.dados_calculo)}<p>${esc(d.formula)}</p><ul>${(d.confirmar||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details><p>Confiança contextual: ${percentage(d.confianca)}.</p>`;
}
function publicEvidence(p){
  if(!p)return '<p class="source-note">Sem API externa específica integrada para este índice. Os sinais utilizados abaixo são cadastrais, declarados ou hipóteses do modelo.</p>';
  const links=String(p.fonte||'').split(' | ').filter(url=>/^https:\/\//.test(url));
  const m=p.parametros||{};
  const labels={...LABELS,frequencia_rajada_forte:`Dias com rajada ≥${m.rajada_forte_kmh??'limiar não disponível'} km/h / dias válidos`,frequencia_rajada_severa:`Dias com rajada ≥${m.rajada_severa_kmh??'limiar não disponível'} km/h / dias válidos`,frequencia_vento_chuva:`Dias com vento ≥${m.rajada_chuva_kmh??'limiar não disponível'} km/h e chuva ≥${m.chuva_mm??'limiar não disponível'} mm / dias conjuntos válidos`};
  return `<section class="public-evidence"><h4>Referência pública e dados disponíveis</h4><p>${esc(p.modo_acesso)}</p><p><strong>${esc(p.condicao||'')}</strong></p><p><strong>Período:</strong> ${esc(p.periodo||'Não disponível')} · <strong>Abrangência:</strong> ${esc(p.granularidade||'Não disponível')}.</p><p>${Object.entries(p.vinculo||{}).map(([k,v])=>`${esc(k)}: ${esc(v??'Não disponível')}`).join(' · ')}</p>
    ${links.length?links.map(url=>`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">Consultar fonte oficial ↗</a>`).join(' · '):'<p>Sem fonte externa vinculada disponível para esta unidade.</p>'}
    <div class="audit-table-wrap"><table class="audit-table"><caption>Valores da referência armazenada (não são uma consulta ao vivo)</caption><thead><tr><th>Indicador / dado</th><th>Valor da fonte</th></tr></thead><tbody>${Object.entries(p.dados||{}).filter(([k])=>!k.startsWith('sha256')).map(([k,v])=>`<tr><th scope="row">${esc(labels[k]||k)}<small><code>${esc(k)}</code></small></th><td>${value(v,null,k)}<small class="source-raw">Conteúdo original: <code>${esc(p.dados_originais?.[k]??v??'(ausente)')}</code></small><p class="source-meaning">${esc(MEANINGS[k]||'Metadado da referência armazenada; consulte a metodologia da fonte para sua definição.')}</p></td></tr>`).join('')}</tbody></table></div>
    ${p.metodologia?`<details><summary>Metodologia da referência</summary><p>${esc(p.metodologia)}</p></details>`:''}<details><summary>Arquivo e integridade da referência</summary><p><code>${esc(p.arquivo)}</code> · SHA-256 do snapshot: <code>${esc(p.sha256_snapshot||'Não disponível')}</code></p>${Object.entries(p.dados).filter(([k])=>k.startsWith('sha256')).map(([k,v])=>`<p>${esc(k)}: <code>${esc(v||'Não disponível')}</code></p>`).join('')}</details></section>`;
}
export function indexEvidence(code,s){
  return `<article class="index-card report-index" data-index-code="${esc(code)}"><header><h3>${esc(s.nome)}</h3><p><strong>${decimal(s.prioridade,1)}%</strong> · ${esc(s.classe)}</p><progress max="100" value="${s.prioridade}" aria-label="${esc(s.nome)}: ${decimal(s.prioridade,1)}%"></progress><small>Sensibilidade ${decimal(s.prioridade_min,1)}%–${decimal(s.prioridade_max,1)}% · Confiança ${percentage(s.confianca,1)}</small></header><p class="source-note">Escalas do modelo em porcentagem: 0% é o mínimo e 100% o máximo de prioridade, exposição, impacto ou vulnerabilidade. Não representam probabilidade de sinistro. Valores em reais, quantidades e classes da fonte mantêm suas unidades; o conteúdo original das células é preservado para conferência.</p>
    ${s.qualidade_seguranca?`<aside role="note"><strong>Base territorial: ${esc(QUALITY_STATES[s.qualidade_seguranca.status]||s.qualidade_seguranca.status)}</strong><p>${(s.qualidade_seguranca.motivos||[]).map(esc).join(' ')}</p><p>Avaliação em ${esc(s.qualidade_seguranca.data_analise)} · Política ${esc(s.qualidade_seguranca.politica)}. A confiança exibida é um peso do modelo; não é precisão estatística.</p></aside>`:''}
    <h4>O que essa pontuação significa para esta unidade</h4><p class="context-reading">${esc(s.leitura_contextual||s.justificativa)}</p><p>${esc(s.explicacao_contextual||'')}</p><p>O cenário usa ${s.valor_exposto_brl==null?'impacto financeiro ainda desconhecido':money(s.valor_exposto_brl)} como exposição contextual; o impacto normalizado efetivo é ${percentage(s.impacto_normalizado)}. A prioridade ${decimal(s.prioridade,1)}% expressa necessidade de proteção, sem estimar chance de sinistro.</p>
    ${publicEvidence(s.referencia_publica)}<details class="local-evidence" open><summary>Dados da empresa e declarações que contextualizam este índice</summary>${evidenceRows(s.evidencias)}<h4>Respostas consideradas</h4>${dataTree(s.respostas_utilizadas)}<p>“Não disponível” significa que a resposta não foi presumida.</p></details>
    <details class="technical-evidence"><summary>Memória técnica: fatores, pesos e cálculo</summary><p>${esc(s.justificativa)}</p><p>Exposição ao evento (R) = ${percentage(s.risco_evento_relativo)} · Impacto (I) = ${percentage(s.impacto_normalizado)} · Vulnerabilidade (V) = ${percentage(s.vulnerabilidade)}.</p><p>Base ${decimal(s.decomposicao.base_pontos)} pontos percentuais + interação ${decimal(s.decomposicao.interacao_pontos)} pontos percentuais + ajuste do limite ${decimal(s.decomposicao.efeito_limite_pontos)} pontos percentuais = ${decimal(s.prioridade)}%.</p><p>Na fórmula abaixo os percentuais são divididos por 100 para o cálculo: 50% equivale a 0,5.</p><p><code>${esc(s.formula)}</code></p>
    ${s.fatores_evento.map(f=>`<section class="factor-evidence"><h4>${esc(f.nome)}</h4>${dataTree(f.valor_original,f.nome==='Dependência digital'?'dependencia_digital_pct':f.nome==='Exposição digital contextual'?'probabilidade_vinculo':f.nome)}<p>Normalizado: ${percentage(f.valor_normalizado)} · Peso no evento: ${percentage(f.peso_evento)} · Contribuição: ${percentage(f.contribuicao_evento)}. Confiança: ${percentage(f.confianca)}.</p><p>${esc(f.transformacao)}. ${esc(f.observacao)}</p></section>`).join('')}
    <h4>Dados e transformação do impacto</h4>${dataTree(s.fator_impacto.valor_original)}<p>${esc(s.fator_impacto.transformacao)}. ${esc(s.fator_impacto.observacao)}</p><h4>Vulnerabilidade</h4>${dataTree(s.fator_vulnerabilidade.valor_original)}<p>${esc(s.fator_vulnerabilidade.transformacao)}. ${esc(s.fator_vulnerabilidade.observacao)}</p></details></article>`;
}
export function assetEvidence(trace){
  if(!trace)return '';
  return `<details class="result-details asset-evidence"><summary>Rastrear bens: registros, valores e ponderação</summary><p>${esc(trace.formula_bens)}</p><p>${esc(trace.observacao)}</p><p>${trace.bens_cadastrais_utilizados?'O agregado cadastral foi utilizado neste cenário.':'Os registros abaixo são referência cadastral; o agregado foi substituído, excluído pelo escopo ou não está disponível. Não será somado novamente.'}</p>
    ${trace.bens.length?`<div class="audit-table-wrap"><table class="audit-table"><caption>Bens vinculados somente à empresa e unidade selecionadas</caption><thead><tr><th>Bem / tipo</th><th>Valor cadastrado</th><th>Peso estimado de vínculo</th><th>Valor × vínculo</th><th>Confiança do vínculo</th></tr></thead><tbody>${trace.bens.map(b=>`<tr><th scope="row">${esc(b.bem_id)}<small>${esc(b.tipo_bem)}</small></th><td>${value(b.valor_cadastrado,'BRL')}</td><td>${value(b.probabilidade_vinculo,'proporcao')}<small>Parcela atribuída à unidade; não é chance de sinistro.</small></td><td>${value(b.valor_ponderado,'BRL')}</td><td>${esc(b.confianca_vinculo||'Não disponível')}</td></tr>`).join('')}</tbody></table></div>`:'<p>Sem registros de bens vinculados disponíveis para esta simulação.</p>'}<p>Fonte: <code>${esc(trace.arquivo_bens)}</code> · ${Object.values(trace.vinculo).filter(Boolean).map(esc).join(' / ')}.</p><p>SHA-256: <code>${esc(trace.sha256_bens||'Não disponível')}</code></p></details>`;
}
