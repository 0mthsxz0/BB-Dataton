# Plano de melhoria da busca inteligente

Data: 29/10/2026. Escopo: identificação assistida de atividades do catálogo na cotação empresarial.

## Objetivo

Permitir que a pessoa descreva seu negócio com suas próprias palavras, receba até três alternativas relevantes e confirme a atividade e a subatividade com clareza. Quando faltar informação, fazer uma pergunta que realmente ajude a diferenciar as alternativas.

## Diagnóstico verificado

O motor atual é local e determinístico, com normalização, pesos por raridade de termos, conceitos por expressões regulares e ajustes específicos por código. O servidor usa esse mesmo motor em POST /api/atividades/buscar. A interface exibe sugestões e perguntas, mas não tem respostas estruturadas para refinamento.

Reprodução direta no motor atual:

| Entrada | Resultado observado | Problema |
| --- | --- | --- |
| Vendo remedios | Nenhuma sugestão | Falta equivalência entre remédio e medicamento |
| Vendo medicamentos | Atividade 476; confiança strong | A troca de uma palavra muda completamente o resultado |
| Tenho uma farmacia | Nenhuma sugestão | A exigência de dois termos úteis ocorre antes da identificação do conceito |
| remedios | Nenhuma sugestão | Entrada curta é descartada sem considerar seu conteúdo |
| Vendo remedios para animais | Nenhuma sugestão | Falta compreensão combinada do produto e público |
| Não vendo medicamentos, vendo cosméticos | Nenhuma sugestão | A remoção de negações por quantidade fixa de palavras pode consumir parte da afirmação seguinte |

Os 21 testes em tests/activity-search.test.js passaram na análise. Isso comprova os cenários existentes, mas não mede a qualidade sobre descrições variadas.

Outras limitações observadas no código: cerca de vinte grupos de conceitos; tolerância a erros no nome da atividade, mas não equivalente na descrição; confiança derivada de pontuação e distância entre candidatos sem calibração; interpretação da operação por prioridade fixa, que simplifica negócios mistos. A interface também mantém sugestões anteriores quando a descrição é editada.

## Etapa 1 — Corrigir as falhas fundamentais

Prioridade máxima. Entrega inicial sem dependência de serviço externo.

1. Separar vocabulário do algoritmo: criar um dicionário versionado de sinônimos, expressões populares, exemplos e exclusões, sempre ligado a identificadores existentes no catálogo. Incluir remédio/medicamento, conserto/reparo e outros termos verificados por segmento.
2. Substituir o bloqueio por número de palavras por avaliação de evidência: “farmácia” pode gerar uma sugestão; “vendo coisas” precisa de esclarecimento.
3. Preservar limites de frases e orações antes de remover pontuação. Aplicar negação ao trecho correspondente, preservando a afirmação após vírgula, ponto ou “mas”.
4. Aplicar correção aproximada controlada na descrição. Priorizar correspondência exata; evitar que uma aproximação fraca do produto seja tratada como evidência forte.
5. Tratar termos contraditórios e atividades mistas sem escolher a primeira operação detectada. Perguntar qual atividade predomina quando essa resposta mudar a escolha.
6. Manter íntegros os 970 registros e os 1.007 vínculos existentes. Não alterar códigos nem criar subatividades.

Aceite: os casos reproduzidos acima recebem sugestão compatível ou pergunta específica; a descrição negativa preserva cosméticos como evidência positiva; os testes atuais continuam passando.

## Etapa 2 — Melhorar relevância e esclarecimento

Organizar o motor em etapas independentes: interpretar descrição → recuperar candidatos → ordenar → avaliar ambiguidade → gerar pergunta e explicação.

Extrair produto/serviço, operação, público e canal de atendimento como evidências separadas, cada uma com o trecho de origem. Diferenciar varejo, atacado, fabricação e reparação sem confundir o local de trabalho com a atividade econômica.

Recuperar candidatos por nomes, subatividades, sinônimos e expressões compostas. Ajustar pesos em um conjunto de desenvolvimento e avaliar em um conjunto separado. Evitar expandir sinônimos de maneira tão ampla que candidatos irrelevantes ganhem vantagem.

Produzir explicações verificáveis: “Você informou venda de medicamentos; esta atividade inclui farmácias e drogarias”. Quando houver conflito, explicar a diferença entre alternativas. Não apresentar pontuação interna como probabilidade de acerto.

Gerar uma pergunta por vez, escolhida pela capacidade de separar candidatos. Exemplos: “Você vende ao consumidor ou para outras empresas revenderem?”; “Os medicamentos são para pessoas ou animais?”. Se a resposta não permitir distinguir itens do catálogo, indicar a limitação e oferecer busca por nome.

Contrato proposto, com migração compatível: preservar results, confidence e question; adicionar evidências estruturadas, tipo de esclarecimento, opções de resposta, versão do motor e versão do catálogo. Respostas devem passar pelo motor novamente, combinadas com o contexto anterior. Validar sempre o vínculo entre atividade e subatividade.

Aceite: perguntas dependem da ambiguidade real; uma resposta altera a busca de forma previsível; nenhuma atividade ou relação fora do catálogo pode ser retornada.

## Etapa 3 — Tornar a interface orientada à decisão

- Exibir exemplos curtos e variados antes da busca, como “Vendo remédios”, “Conserto celulares” e “Faço bolos por encomenda”.
- Mostrar no máximo três cartões, com nome legível, motivo da indicação e diferença relevante entre opções.
- Apresentar esclarecimentos como botões e permitir resposta livre. Preservar a descrição e oferecer voltar para corrigir uma resposta.
- Separar confirmação de atividade e confirmação de subatividade quando faltar evidência. Uma única subatividade no catálogo não comprova que a descrição informa suas características.
- Ao editar a descrição, invalidar as sugestões anteriores ou marcá-las claramente como desatualizadas. Impedir aplicação de resposta de requisição antiga após uma busca mais recente.
- Diferenciar ausência de correspondência, dúvida e falha de conexão. Oferecer nova tentativa e acesso à lista; considerar fallback local com o mesmo catálogo e versão, identificado na interface.
- Validar navegação por teclado, anúncio de resultados e carregamento por leitor de tela, foco após perguntas e usabilidade em celular.

Fluxo esperado para o caso da imagem: “Vendo remédios” → sugestão de farmácia/drogaria quando sustentada pelo catálogo → explicação simples → pergunta sobre público apenas se houver alternativa relevante → confirmação explícita → subatividade quando necessária.

## Etapa 4 — Medir e evoluir com evidências

Criar uma base inicial de pelo menos 200 descrições revisadas, incluindo entradas curtas, linguagem popular, erros de digitação, negação, vários serviços, termos ambíguos e atividades ausentes do catálogo. Cobrir os segmentos prioritários e ampliar a cobertura antes de alegar qualidade sobre todo o catálogo.

Cada caso deve registrar alternativas aceitáveis, opções indevidas, informação faltante e comportamento esperado: sugerir, perguntar ou informar ausência. Separar desenvolvimento e avaliação por famílias de paráfrases para evitar vazamento entre conjuntos. Manter as falhas reproduzidas como regressões permanentes.

Metas iniciais propostas, a confirmar após medir a linha de base:

| Indicador | Meta de aceite |
| --- | --- |
| Primeiro resultado correto em descrições inequívocas | Pelo menos 90% |
| Alternativa correta entre as três sugestões em casos respondíveis | Pelo menos 97% |
| Sugestão forte indevida em casos ambíguos ou sem cobertura | No máximo 2% |
| Identificadores e vínculos válidos | 100% |
| Busca local no percentil 95 | Até 300 ms no dispositivo de referência definido |
| Ganho após esclarecimento | Medir antes/depois; resposta deve reduzir candidatos ou resolver a dúvida |

Registrar contagens de buscas, ausência de resultados, esclarecimentos, escolhas e correções manuais, com versões do catálogo/motor. Esses eventos são sinais de uso, não prova de acerto. Evitar armazenar descrições livres por padrão; qualquer coleta de exemplos precisa de finalidade, acesso e retenção definidos.

## Evolução semântica opcional

Depois da linha de base, comparar o motor melhorado com busca híbrida lexical e semântica sobre o mesmo catálogo e o mesmo conjunto de avaliação. Adotar embeddings apenas se houver ganho mensurável que justifique custo, latência, privacidade e manutenção.

Um modelo generativo, caso necessário, pode ajudar a extrair intenção ou formular esclarecimentos. A recuperação e a validação continuam limitadas ao catálogo. Definir timeout, fallback determinístico, validação de saída e tratamento da descrição como dados, nunca como instrução. Escolher provedor e infraestrutura em uma etapa posterior de pesquisa técnica.

## Ordem de execução e arquivos

1. Base de avaliação, correções fundamentais e testes: public/activity-search.js, novo dicionário de vocabulário e tests/activity-search.test.js.
2. Evidências, ordenação e esclarecimento estruturado: motor e contrato em server.mjs, com testes da API.
3. Refinamento e estados da interface: ActivityPicker em public/quote.js e estilos em public/quote.css; verificação no navegador, celular e teclado.
4. Avaliação final, instrumentação mínima e documentação: registrar resultados por segmento e comparar com a linha de base.
5. Experimento semântico separado, condicionado a lacunas persistentes na avaliação.

Estimativa preliminar: 5 a 8 dias úteis de desenvolvimento e validação para as quatro primeiras entregas, sujeita à revisão do vocabulário e dos exemplos. O experimento semântico tem estimativa própria após a linha de base.

## Critério de conclusão

O caso “vendo remédios” funciona; descrições curtas informativas não são descartadas; negações não apagam afirmações; dúvidas geram perguntas específicas; nenhum código é inventado; resultados desatualizados não podem ser aplicados; métricas são publicadas com amostra e limitações. A busca orienta a escolha e mantém a confirmação do usuário, sem decidir aceitação de seguro ou enquadramento contratual.

Atualização de implementação: as correções do motor, refinamento estruturado, estados de interface, fallback local explícito, contadores de sessão e avaliação sintética foram implementados. Consulte COTACAO.md e docs/evidence/activity-evaluation.json. Permanecem para evolução a amostra independente revisada com usuários reais, a calibração de confiança e o experimento semântico condicionado aos resultados.
