// Resume the customer questionnaire with the selected unit's available data.
export function startIdRefinement(state, response, catalog) {
  const report = response?.relatorio;
  if (!report || !response.empresaId || !response.imovelId)
    throw new Error('Selecione um relatório por ID antes de refinar.');
  state.idJourney = true;
  state.sourceKey = response.empresaId + '|' + response.imovelId;
  state.city = report.localizacao?.municipio_real || '';
  state.uf = report.localizacao?.uf_real || '';
  state.cnae = report.atividade?.cnaeUtilizado || '';
  state.prefilledFields = [];
  for (const [key, value] of Object.entries({...report.preenchimento, ...report.confirmacoesDisponiveis, ...report.complemento})) {
    if (value == null || value === '' || !(key in state)) continue;
    state[key] = typeof value === 'boolean' ? (value ? 'yes' : 'no') : String(value);
    state.prefilledFields.push(key);
  }
  const groups = {RESTAURANTE:'625', FARMACIA:'476', MERCADO:'909', VAREJO_MODA:'484', CLINICA:'690', BELEZA:'641', ESCOLA_CURSO:'728', ESCRITORIO:'674', ELETRONICOS:'1007'};
  const activity = catalog.activities.find(a => a.id === groups[report.cadastro?.grupo_atividade]);
  state.activityId = activity?.id || '';
  state.subactivityId = activity?.subactivities.length === 1 ? activity.subactivities[0].id : '';
  return state;
}

export function recommendationEndpoint(state) {
  return state.idJourney ? '/api/demo/recomendacao' : '/api/recomendacao';
}
