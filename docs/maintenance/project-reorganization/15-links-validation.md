# 15 — Validação de links (FASE 2)

## Verificador

`frontend/scripts/check_markdown_links.py` resolve links relativos de arquivo/pasta em
todos os `.md` e reporta os inexistentes. Ignora http(s)/mailto, âncoras puras e alvos que
não são caminhos (sem `/` nem extensão — ex.: citações por UUID).

## Resultado

```text
=== check_markdown_links === root=agrotrace-carbon
broken_count=0
```

## Links pré-existentes corrigidos

- `agrotrace-carbon-wrappers-service/README.md`: 3 links órfãos → ponteiro ao doc canônico.
- `agrotrace-carbon-wrappers-service/docs/README.md`: 2 links de runbooks inexistentes removidos.

## Referências antigas remanescentes (aceitas)

Menções textuais a caminhos antigos (`docs/auditoria-*`, `conceptual_model_mrv.md`,
`filter_architecture_mrv.md`) permanecem **apenas** dentro de conteúdo de auditoria:

- `docs/audits/current/*` (auditoria pós-implementação, gerada/histórica).
- `docs/audits/archive/2026-08-03-capitulo-5/*` (auditoria histórica).

Não são links de arquivo (são descrições/citações do estado à época) e não foram
reescritos, para preservar a evidência histórica. Nenhuma documentação **canônica/ativa**
referencia caminhos removidos.
