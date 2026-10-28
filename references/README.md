# Referências públicas congeladas

Snapshots preparados em 28/10/2026 para uso acadêmico. Não contêm dados das empresas do desafio.

- seguranca_municipal.csv: 27 capitais, IBGE/SIDRA 8508/8510/8512, ano 2021; proxy de vitimização domiciliar e segurança relativa.
- clima_municipal.csv: dez municípios, ERA5 via Open-Meteo, 1996–2025; frequências, completude, coordenadas públicas/células e cenários alternativos.
- nr4_cnae.csv: 673 classes extraídas da edição do PDF NR-4 indicada nas linhas, com página e hash; uso contextual ocupacional.
- manifesto_fontes.json: hashes dos snapshots e dos arquivos públicos baixados. O cache integral fica localmente em data/referencias/cache.

Para reconstruir: python scripts/preparar_referencias.py --dados CAMINHO_DOS_CSVS. O preparador não envia registros empresariais às fontes; geocodifica apenas nomes de municípios públicos.

Fontes: https://sidra.ibge.gov.br/tabela/8508, https://sidra.ibge.gov.br/tabela/8510, https://sidra.ibge.gov.br/tabela/8512, https://open-meteo.com/en/docs/historical-weather-api e o URL oficial do MTE registrado em fonte_nr4.

Dados climáticos: atribuição Open-Meteo e Copernicus/ECMWF ERA5; respeitar condições de uso da fonte. Os indicadores calculados e seus pesos são da equipe, não índices oficiais dos fornecedores nem probabilidades de sinistro.
