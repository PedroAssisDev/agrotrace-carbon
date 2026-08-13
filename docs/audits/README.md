# Auditorias

Esta área separa a auditoria vigente das auditorias históricas.

| Pasta | Conteúdo | Status |
|-------|----------|--------|
| [`current/`](current/) | Auditoria pós-implementação (mais recente e validada) | atual |
| [`archive/`](archive/) | Auditorias anteriores, preservadas para rastreabilidade | histórico |

## Auditoria atual

`current/` contém a auditoria pós-implementação alinhada à numeração oficial da
dissertação (RF001–RF021, RNF001–RNF012, CE1–CE5). Os documentos Markdown são
**gerados** a partir de `current/09-resultados.json` e `current/_regressao.json`
(ou `regressao.json`) pelo script `current/_gen_reports.py` — não edite os `.md`
manualmente.

Fonte de verdade dos resultados: `current/09-resultados.json`.

Para o estado **atual do software** (não só da auditoria Cap. 5), prefira
[`../limitations.md`](../limitations.md) e [`../architecture/overview.md`](../architecture/overview.md).

## Auditorias históricas

`archive/<data-ou-versao>/` guarda auditorias superadas. Cada pasta possui um
`README.md` com data, versão analisada, contexto, status histórico, limitações e
documento sucessor. Resultados e falhas são preservados como foram observados —
não são reescritos para parecerem atuais.
