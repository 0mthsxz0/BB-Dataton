# Integração do motor principal com o banco público de segurança

## Comportamento entregue

O motor da main consulta o SQLite público por código IBGE, em leitura somente. Empresas, estabelecimentos, bens e confirmações continuam no consumidor; não são gravados nesse banco. Não há download durante uma recomendação.

A configuração padrão é **complementar**: o relatório exibe contexto, fontes, janela, cobertura, versão e limitações, preservando a pontuação atual. No modo **referencia_validada**, somente uma referência de roubo em comércio que passe pela política `seguranca-1.0` pode alimentar o evento territorial de roubo. Taxas por população, veículo/carga, vítimas e Mosler nunca são atribuídos ao campo empresarial antigo.

Ausência de banco, manifesto divergente, versão incompatível, município ausente ou referência incompleta não interrompem a recomendação. O motor continua avaliando as referências CSV existentes; quando não há uma referência elegível, o componente territorial continua desconhecido, com confiança zero. A confiança de respostas do formulário é um componente separado.

Os índices de vendaval, empregador e vidros, as obrigatórias, a triagem e a compatibilidade dos adicionais conservam suas regras. O contexto municipal não calcula preço, probabilidade de sinistro ou risco por rua.

## Arquitetura

```text
Banco público SQLite + manifesto de release
                 │ somente leitura, código IBGE
                 ▼
contexto_seguranca.py
    ├─ contexto criminal municipal → relatório complementar
    └─ referência empresarial → política existente → evento de roubo

Cadastro/respostas → avaliação Mosler técnica → relatório complementar
```

Não copiar o pacote Python `seguranca/` da outra branch sobre `seguranca.py` da main. A conexão usa um módulo próprio e o contrato do SQLite; as interfaces das branches não precisam ser mescladas.

## Publicar uma versão dos dados

Execute com o banco original já coletado e auditado, fora do diretório de código versionado:

```bash
python scripts/publicar_base_seguranca.py \
  --origem /caminho/banco-publico.sqlite \
  --saida output/release-seguranca-2025-v1 \
  --versao 2025-v1
```

O script faz um backup consistente, sem modificar o original, e gera:

- `seguranca.sqlite`;
- `seguranca.sqlite.manifesto.json`.

O manifesto declara formato `bb-seguranca-publica`, schema `1`, versão dos dados, instante de geração e SHA-256. A validação confere schema, integridade e ausência de colunas identificadoras de clientes. Um banco estruturalmente válido pode ter cobertura parcial: publicação não certifica que todos os municípios possuem indicador utilizável.

Publicar esses dois arquivos juntos como artefato de uma release ou em armazenamento autorizado. Não adicionar o SQLite ao Git; `data/` e `output/` permanecem ignorados. Hash comprova integridade em relação ao manifesto, não a autenticidade das fontes; o produtor deve revisar originais e metodologia antes de publicar.

## Instalar no servidor da main

Copie os dois arquivos para uma pasta local e execute:

```bash
python scripts/instalar_base_seguranca.py \
  --pacote /caminho/release-seguranca-2025-v1 \
  --destino data/seguranca/releases
```

A instalação valida antes e depois da cópia e cria um diretório pelo hash do banco. Não sobrescreve a versão anterior. O resultado JSON informa o caminho instalado.

Configure no ambiente do processo:

```bash
export BB_SEGURANCA_DB="/caminho/instalado/seguranca.sqlite"
export BB_SEGURANCA_MODO="complementar"
```

No PowerShell:

```powershell
$env:BB_SEGURANCA_DB = "C:\caminho\instalado\seguranca.sqlite"
$env:BB_SEGURANCA_MODO = "complementar"
```

Reinicie o Streamlit e/ou o servidor Node para aplicar a configuração. Não há carregamento automático de `.env` neste fluxo.

Para retorno à versão anterior, aponte `BB_SEGURANCA_DB` para o diretório anterior e reinicie. O modo complementar permite comparar os dados antes de habilitar influência nas recomendações.

## Habilitar influência na prioridade de roubo

Depois da revisão de cobertura e da comparação dos resultados:

```bash
export BB_SEGURANCA_MODO="referencia_validada"
```

A referência deve estar na tabela opcional `referencias_motor(codigo_ibge, ano, dados)`, produzida pela preparação da branch de segurança. `dados` contém o objeto empresarial já normalizado: categoria, contagem, denominador de estabelecimentos do mesmo ano, doze meses, fontes oficiais, hashes, taxa e transformação. A cada análise o motor valida de novo município/UF, validade temporal e contrato.

O modo não converte outros indicadores em roubo em comércio. Se a referência não for elegível, ela não substitui a referência existente. Não há multiplicador aplicado sobre a prioridade final.

## Execução em lote

```bash
python cli.py --dados /caminho/csvs-do-consumidor \
  --banco-seguranca /caminho/instalado/seguranca.sqlite \
  --modo-seguranca complementar --saida output/analise
```

A auditoria registra contexto, estado de uso, versão do banco, hash e avaliação Mosler. O manifesto da exportação registra modo e releases utilizadas; as colunas dos templates oficiais permanecem preservadas.

## Interface e API

No Streamlit, o painel **Disponibilidade do banco público de segurança** mostra instalação, versão e contagens. Na análise de uma unidade, **Contexto público de segurança e avaliação Mosler** mostra disponibilidade e influência efetiva na recomendação. A assinatura do banco/manifesto e o modo entram na invalidação do cache do painel.

O relatório interno do formulário também exibe esse bloco, incluindo a distinção entre zero observado e valor ausente. O resumo externo conserva a minimização de dados internos.

Consulta HTTP local, sem identificadores de empresas:

```http
POST /api/seguranca/municipio
Content-Type: application/json

{"codigoIBGE":"3550308","uf":"SP"}
```

O endpoint conserva os controles de Host/Origin e limites existentes. Não aceita caminho de banco pelo cliente. O caminho é configuração do servidor. A abertura do SQLite usa somente leitura e não cria um arquivo vazio quando o caminho é inválido.

Estados relevantes: `NAO_CONFIGURADO`, `BASE_INDISPONIVEL`, `LOCALIZACAO_INVALIDA`, `MUNICIPIO_NAO_ENCONTRADO`, `SEM_SERIE_MUNICIPAL`, `PARCIAL` e `DISPONIVEL`. `DISPONIVEL` significa referência empresarial elegível, não cobertura nacional ou calibração atuarial.

As séries contextuais exibem meses observados e somente somam uma janela anual completa quando há doze competências, com proveniência completa em um único snapshot. Fontes diferentes na mesma janela não são somadas como uma série anual validada. Taxa por população é exibida apenas com denominador positivo do mesmo ano; ano diferente permanece documentado, sem taxa. Séries com mais de três meses de defasagem recebem aviso editorial `DESATUALIZADO`; a validade da referência empresarial segue a política própria de 24 meses após o ano observado.

## Mosler separado

`avaliacao_mosler.py` oferece o contrato técnico `mosler-tecnico-declarado-1.0`. Recebe seis notas inteiras F/S/P/E/A/V, evidência por critério, avaliador e data; retorna ER, normalização e faixa. Não estima notas a partir de CNAE, patrimônio ou contexto territorial.

```python
avaliacao = {
    "criterios": {
        # Repetir F, S, P, E, A e V, com nota e evidência específicas.
        "F": {"nota": 3, "evidencia": "Justificativa técnica da função"}
    },
    "avaliador": "Responsável técnico",
    "data_avaliacao": "2026-10-29"
}
```

O exemplo é incompleto por desenho: até registrar os seis critérios, o resultado é pendente/inválido. Uma avaliação técnica completa pode ser anexada ao registro do consumidor na chave `avaliacao_mosler`; não é armazenada no banco público. Não foi criado um novo questionário de notas para o cliente final nesta etapa.

Este contrato manual é distinto da adaptação ponderada IBGE/SINESP/CSV da branch de dados. Não chama o índice CRITIC de agressão Mosler. A avaliação permanece complementar e não altera plano ou adicionais, mesmo quando completa; usar Mosler na decisão exigirá outra estratégia validada para evitar dupla contagem.

## Verificação com a base real disponível

Foi publicado e instalado um pacote local `2025-vde-parcial.1` usando o banco da branch de segurança com 69.510 registros brutos de roubo do SINESP 2025. O schema/manifesto foram aceitos, o endpoint HTTP respondeu e o Streamlit abriu a base de desenvolvimento do consumidor sem erros.

O cadastro municipal nessa cópia ainda está vazio. A consulta retorna `MUNICIPIO_NAO_ENCONTRADO`, e nenhum indicador foi inventado ou aplicado. Isso comprova integração e tratamento de ausência; não comprova cobertura criminal pronta. Os bloqueios de fontes continuam sendo um trabalho independente de coleta.

A evidência agregada, sem dados individuais de empresas, está em [banco-real-parcial.json](evidencias-integracao-seguranca/banco-real-parcial.json).

O servidor Node atual inicia um processo Python por consulta; o cache de integridade é por processo. Para bancos muito maiores, medir latência e considerar um serviço Python persistente antes de produção. A instalação por hash permite reutilizar o mesmo arquivo em leitura sem misturar atualizações durante a análise.
