import { fullName, escapeText as esc } from './language.js';
export function customerReport(r){
 if(!r)return null;
 const rec=r.recomendacao,p=r.personalizacao?.pacote;
 const base=p?.coberturas||rec.comparacao.find(c=>c.id===r.planoId)?.coberturas||[];
 const included=(r.personalizacao?.adicionais||[]).filter(x=>x.solicitada);
 const covers=p?.protecoes?.map(x=>fullName(x.nome))||[...base.map(k=>fullName(rec.necessidades[k]?.nome||k)),...included.map(x=>fullName(x.name))];
 return {vidros:r.vidrosDeclarados||null,plano:({ESSENCIAL:'Empresarial Essencial',PRATICO:'Empresarial Prático',TOTAL:'Empresarial Total'})[p?.plano||rec.plano_recomendado],encaminhamento:!!rec.indicacao_bloqueada,coberturas:[...new Set(covers)],vigenciaAnos:p?.vigencia_anos||1,pendencias:!!((r.avisos||[]).length||(rec.perguntas_confirmacao||[]).length),observacao:'Simulação de um pacote personalizado. Preço, franquias, limites e aceitação serão confirmados na cotação oficial. A proteção segue as condições do contrato.'};
}
export function customerRecommendationView(result){
 const r=customerReport(result);if(!r)return '';
 return `<section class="recommendation customer-recommendation" aria-label="Sua recomendação"><p class="result-eyebrow">Proteção pensada para seu negócio</p><h2>${r.encaminhamento?'Vamos conferir alguns pontos com um especialista':'Seu pacote personalizado'}</h2><p>${r.encaminhamento?'Há condições que precisam de avaliação antes de prosseguir.':'Reunimos em um só pacote as proteções pertinentes às suas respostas, para cuidar do patrimônio e do funcionamento da sua empresa.'}</p><p class="package-total"><strong>${r.coberturas.length} coberturas</strong> · ${r.vigenciaAnos} ${r.vigenciaAnos===1?'ano':'anos'}</p><h3>Como seu negócio fica protegido</h3><ul class="unified-coverages">${r.coberturas.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>${r.vidros?.quantidade!=null?`<p>Você informou aproximadamente ${esc(r.vidros.quantidade)} itens de vidro. O valor de reposição será confirmado quando necessário.</p>`:''}${r.pendencias?'<p>Algumas informações ainda precisam de confirmação para concluir a cotação.</p>':''}<p class="catalog-note">${esc(r.observacao)}</p></section>`;
}
