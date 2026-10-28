# Validação da atualização 0.2

Executada localmente em 28/10/2026, Python 3.12. A suíte passou em 50 testes, incluindo fluxo do Streamlit e exportação. As fixtures de testes são artificiais e isoladas dos CSVs privados e de consultas à rede.

| Verificação | Desenvolvimento | Teste comum |
|---|---:|---:|
| Estabelecimentos processados | 2.978 | 144 |
| Linhas do template de coberturas | 15.102 | 728 |
| Com referência municipal de segurança | 2.978 | 144 |
| Com referência climática | 2.978 | 144 |
| Com correspondência NR-4 | 2.978 | 144 |
| Essencial sugerido | 2.873 | 140 |
| Prático sugerido | 104 | 4 |
| Total sugerido | 1 | 0 |
| Mudanças de plano frente à saída local v0.1 | 141 | 5 |

As diferenças frente à v0.1 combinam mudança da fórmula, do universo decisório e inclusão de dados públicos. Não isolam o efeito de cada alteração nem comprovam precisão preditiva superior. Os cortes não foram ajustados para produzir essas proporções.

Em todas as unidades foram conferidos quatro índices, nove dimensionamentos, notas finitas entre 0 e 100, limites de sensibilidade contendo a nota central, reconstrução da decomposição e presença de todas as coberturas fixas do plano escolhido. Não houve duplicação de empresa-estabelecimento nas saídas. Colunas dos templates originais foram preservadas.

As dez séries municipais têm 10.958 dias esperados e completos, com rajadas/chuva de 1996–2025. Referência de segurança: PNAD/IBGE 2021, proxy domiciliar. Referência ocupacional: 673 classes extraídas do PDF indicado da NR-4, incluindo descrições em múltiplas linhas. Arquivos e hashes em references/.

Confiança média dos quatro índices: aproximadamente 41,6% no desenvolvimento e 41,4% no teste. Isso mede a qualidade contextual da evidência no modelo, não acurácia. Caixa/reservas, valores de danos a terceiros, inventário de vidros e resistência dos telhados continuam incompletos. Aceitação contratual e preço continuam pendentes.

Reprodução: executar pytest e os comandos de processamento em lote do README, mantendo os mesmos CSVs, snapshots e config_regras.json. As saídas completas ficam localmente em output/atualizacao_desenvolvimento e output/atualizacao_teste, fora do Git.
