// Hipóteses de cenário, sem calibração em sinistros. Não são os pesos CRITIC.
export const SCENARIO = Object.freeze({
  garage: Object.freeze({ sim: 0.85, nao: 1.15 }),
  use: Object.freeze({ interno: 1, externo: 1.2, misto: 1.1 }),
  version: 'hipotese-1',
});

export function relativeNeed(index, value, garage, use, enterpriseValidated = false) {
  if (!enterpriseValidated) return null;
  const amount = Number(value);
  if (typeof index !== 'number' || !Number.isFinite(index) || index < 0 || index > 100
      || value === '' || !Number.isFinite(amount) || amount <= 0
      || !Object.hasOwn(SCENARIO.garage, garage) || !Object.hasOwn(SCENARIO.use, use)) return null;
  // Pontos de exposição relativos por R$1.000 de bens; não reais esperados de perda.
  return { points: (amount / 1000) * (index / 100) * SCENARIO.garage[garage] * SCENARIO.use[use],
    garageFactor: SCENARIO.garage[garage], useFactor: SCENARIO.use[use], version: SCENARIO.version };
}

export function coverageSuggestion(risk, plans) {
  if (risk?.uso_empresarial_validado !== true || typeof risk?.indice_roubo_0_100 !== 'number') return [];
  // Presença contratual do catálogo, sem escolher prêmio/plano por um corte de risco arbitrário.
  return plans.filter(p => p.coverages.includes('10932')).map(p => p.name);
}

export function matchingMunicipality(city, uf, candidates) {
  const normalize = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLocaleLowerCase('pt-BR');
  const found = candidates.filter(c => c.uf === uf && normalize(c.municipio) === normalize(city));
  return found.length === 1 ? found[0] : null;
}
