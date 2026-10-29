# Catálogo público de atividades

Coleta: 28/10/2026. Origem: https://cotacaoseguroempresarial.bbseguros.com.br/home.

- `activities.json`: resposta de `GET /api/simulador/ultron/general/atividade-economica?tpPesquisa=1`, no domínio `apigateway.cld.brasilseg.com.br`.
- `subactivities-by-activity.json`: respostas `lsAlternativa` de `GET` no mesmo recurso com `cdAtividade=<código>&tpPesquisa=3`, para as 970 atividades.
- `subactivities.json`: resposta pública de pesquisa de subatividades com `tpPesquisa=2&txDescritivoPesquisa=`.

As consultas usaram a sessão anônima temporária emitida pelo fluxo normal do aplicativo: `GET /oauth/temp/acesso`, com a origem do próprio formulário. Nenhum formulário pessoal foi enviado. Nenhuma cotação, proposta ou contrato foi criado. Identificadores de sessão ficaram apenas em memória e não constam destes arquivos.

São 970 atividades e 1.007 relações atividade–subatividade. Dez atividades retornaram lista vazia. Há categorias e nomes iguais, vínculos pouco intuitivos e um identificador com espaço inicial; os valores originais foram preservados, sem inferir ou corrigir o enquadramento da seguradora.

Estes são códigos internos da seguradora, **não códigos CNAE**. As descrições por extenso na interface são expansões editoriais; as descrições originais continuam nos campos `sourceLabel` para auditoria. Não se afirma que as expansões sejam nomes oficiais aprovados pela seguradora.

Para gerar novamente a versão consumida pelo navegador, a partir dos snapshots:

```sh
python scripts/preparar_catalogo_cotacao.py
```

O aplicativo funciona offline após iniciar o servidor local e não consulta o serviço da seguradora em tempo de execução.
