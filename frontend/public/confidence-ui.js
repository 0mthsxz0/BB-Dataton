const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const percent = value => Number(value).toLocaleString('pt-BR', {maximumFractionDigits:1}) + '%';
const known = value => value !== null && value !== undefined && value !== '';

export function confidenceView(result) {
  const detail = result.confiancaDados;
  const score = result.recomendacao.confianca_geral * 100;
  const missing = detail?.campos.filter(f => f.pendente && !known(f.valorCadastro)) || [];
  const previous = result.atualizacaoConfianca?.anterior;
  return `<section class="confidence-panel" aria-label="Confiança dos dados e informações a confirmar">
    <div class="confidence-heading"><div><p class="result-eyebrow">Qualidade das evidências da recomendação</p><h3>Confiança dos dados</h3></div>
    <strong class="confidence-score">${percent(score)}</strong></div>
    ${previous != null ? `<p class="confidence-comparison" role="status">Relatório recalculado · Antes: <strong>${percent(previous)}</strong> · Agora: <strong>${percent(score)}</strong>. ${score > previous ? 'As confirmações aumentaram o indicador.' : 'As respostas atualizaram a análise; o indicador pode permanecer igual ou diminuir conforme as evidências.'}</p>` : ''}
    <p class="confidence-description">${esc(detail?.explicacao || 'Este indicador resume a força das evidências usadas na recomendação. Dados incompletos, estimativas e os pesos experimentais do modelo influenciam o resultado.')}</p>
    <div class="confidence-content"><div><h4>Por que este número?</h4>
    <ul>${detail ? detail.motivos.map(m => `<li>${esc(m.texto)}</li>`).join('') || '<li>As informações deste formulário foram confirmadas. O indicador ainda considera os limites e os pesos do modelo.</li>' : '<li>A confiança combina as dez necessidades de proteção. Algumas usam sinais indiretos com pesos conservadores.</li>'}</ul>
    ${missing.length ? `<p><strong>Exemplos sem informação:</strong> ${missing.slice(0,4).map(f => esc(f.label)).join('; ')}${missing.length > 4 ? `; e mais ${missing.length - 4} perguntas no formulário` : ''}.</p>` : ''}</div>
    <div class="confidence-guidance"><h4>Converse com o cliente</h4><p>Confirme as condições do imóvel, a proteção existente, a equipe desta unidade e os valores de reposição. Registre apenas o que o cliente souber informar.</p>
    ${detail ? `<p><strong>${detail.pendentes} informações a confirmar</strong> · ${detail.confirmados} respostas registradas nesta análise.</p>` : ''}</div></div>
    ${detail ? `<details class="confidence-limitations"><summary>Limitações que as respostas não resolvem</summary><ul>${detail.limitacoes.map(text => `<li>${esc(text)}</li>`).join('')}</ul></details>` : '<p>Percentual interno do MVP, sem calibração de precisão estatística.</p>'}
    ${detail ? `<div class="confidence-actions"><button class="btn" type="button" data-confidence-open data-company="${esc(detail.empresaId)}" data-unit="${esc(detail.imovelId)}">Adicionar dados</button><p>O colaborador pode perguntar ao cliente, preencher as respostas e recalcular este relatório.</p></div>` : ''}
  </section>`;
}

function currentValue(field) {
  if (!known(field.valorCadastro)) return 'Não consta no cadastro';
  if (field.tipo === 'number') return Number(field.valorCadastro).toLocaleString('pt-BR', field.inteiro ? {} : {style:'currency',currency:'BRL'});
  return field.opcoes?.find(([value]) => value === field.valorCadastro)?.[1] || String(field.valorCadastro);
}

export function confidenceFormFields(fields) {
  return [...new Set(fields.map(f => f.grupo))].map(group => `<fieldset class="confidence-field-group"><legend>${esc(group)}</legend><div class="form-grid">${fields.filter(f => f.grupo === group).map(f => {
    const id = 'confidence-' + f.id;
    const value = f.valorConfirmado;
    const input = f.tipo === 'number'
      ? `<input id="${id}" name="${esc(f.id)}" type="number" min="0" max="${f.inteiro ? '1000000' : '1000000000000'}" step="${f.inteiro ? '1' : 'any'}" inputmode="${f.inteiro ? 'numeric' : 'decimal'}" value="${known(value) ? esc(value) : ''}" placeholder="Ainda não confirmado" aria-describedby="${id}-help">`
      : `<select id="${id}" name="${esc(f.id)}" aria-describedby="${id}-help"><option value="">Ainda não sei / usar cadastro</option>${(f.tipo === 'boolean' ? [[true,'Sim'],[false,'Não']] : f.opcoes).map(([v,label]) => `<option value="${esc(v)}" ${known(value) && value === v ? 'selected' : ''}>${esc(label)}</option>`).join('')}</select>`;
    return `<div class="qfield"><label for="${id}">${esc(f.label)}</label>${input}<small id="${id}-help">${f.tipo === 'boolean' ? 'Resposta confirmada com o cliente. Em branco, permanece desconhecida.' : `Informação atual: ${esc(currentValue(f))}. Preencha somente se confirmou com o cliente.`}</small></div>`;
  }).join('')}</div></fieldset>`).join('');
}

export function collectConfidenceAnswers(form, fields) {
  const data = new FormData(form);
  const answers = {};
  for (const field of fields) {
    const value = data.get(field.id);
    if (value === null || value === '') continue;
    answers[field.id] = field.tipo === 'boolean' ? value === 'true' : field.tipo === 'number' ? Number(value) : value;
  }
  return answers;
}

export function installConfidenceEditor({getContext, save, onUpdated}) {
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-confidence-open]');
    if (!button) return;
    const context = getContext(button.dataset.company, button.dataset.unit);
    if (!context?.report?.confiancaDados) return;
    document.querySelector('#confidence-dialog')?.remove();
    const detail = context.report.confiancaDados;
    const dialog = document.createElement('dialog');
    dialog.id = 'confidence-dialog';
    dialog.className = 'confidence-dialog';
    dialog.setAttribute('aria-labelledby', 'confidence-dialog-title');
    dialog.innerHTML = `<form class="confidence-form"><header class="confidence-dialog-heading"><div><p class="result-eyebrow">Confirmação com o cliente</p><h2 id="confidence-dialog-title">Adicionar dados ao relatório</h2><p>${esc(detail.empresaId)} · ${esc(detail.imovelId)}</p></div><button type="button" class="back-button" data-confidence-cancel aria-label="Fechar formulário">Fechar ×</button></header>
      <div class="confidence-form-body"><p>Use estas perguntas durante o contato com o cliente. Todos os campos são opcionais: deixe em branco o que ainda não conseguiu confirmar. Zero confirma ausência.</p><p>Valores que já constam no cadastro aparecem como referência. Equipamentos são parte dos bens; estoque fica separado. As respostas ficam nesta sessão e podem ser baixadas no relatório atualizado.</p>
      ${confidenceFormFields(detail.campos)}<p class="quote-error" data-confidence-error role="alert"></p></div>
      <footer class="confidence-dialog-footer"><p data-confidence-status role="status">A análise será recalculada com as respostas confirmadas.</p><div><button type="button" class="btn btn-outline" data-confidence-cancel>Cancelar</button><button type="submit" class="btn">Gerar relatório atualizado</button></div></footer></form>`;
    document.body.append(dialog);
    const form = dialog.querySelector('form');
    let saving = false;
    dialog.querySelectorAll('[data-confidence-cancel]').forEach(b => b.addEventListener('click', () => dialog.close()));
    dialog.addEventListener('cancel', e => { if (saving) e.preventDefault(); });
    dialog.addEventListener('close', () => {dialog.remove(); if (button.isConnected) button.focus();}, {once:true});
    form.addEventListener('submit', async e => {
      e.preventDefault();
      if (saving || !form.reportValidity()) return;
      const answers = collectConfidenceAnswers(form, detail.campos);
      const error = dialog.querySelector('[data-confidence-error]');
      if (!Object.keys(answers).length && !detail.confirmados) {error.textContent = 'Confirme pelo menos uma informação ou cancele para manter o relatório atual.'; return;}
      if (getContext(detail.empresaId, detail.imovelId)?.report !== context.report) {error.textContent = 'O relatório mudou. Feche este formulário e abra os dados da unidade atual.'; return;}
      saving = true;
      error.textContent = '';
      form.setAttribute('aria-busy', 'true');
      const controls = [...form.querySelectorAll('input, select, button')];
      controls.forEach(c => {c.disabled = true;});
      dialog.querySelector('[data-confidence-status]').textContent = 'Recalculando os índices, as pendências e a recomendação…';
      try {
        const result = await save(context, answers);
        if (getContext(detail.empresaId, detail.imovelId)?.report !== context.report) throw new Error('A unidade selecionada mudou. Abra o formulário do relatório atual.');
        const updated = result.relatorio || result;
        updated.atualizacaoConfianca = {anterior:context.report.recomendacao.confianca_geral * 100};
        onUpdated(context, result);
        dialog.close();
        const panel = [...document.querySelectorAll('[data-confidence-open]')].find(b => b.dataset.company === detail.empresaId && b.dataset.unit === detail.imovelId)?.closest('.confidence-panel');
        panel?.scrollIntoView({block:'start',behavior:'smooth'});
        panel?.querySelector('button')?.focus({preventScroll:true});
      } catch (e) {
        error.textContent = e.message;
        dialog.querySelector('[data-confidence-status]').textContent = 'Revise as respostas. O relatório anterior continua disponível.';
      } finally {
        saving = false;
        form.removeAttribute('aria-busy');
        controls.forEach(c => {c.disabled = false;});
      }
    });
    dialog.showModal();
  });
}
