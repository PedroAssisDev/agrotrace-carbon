# 13 — Itens movidos/renomeados (FASE 2)

Todos via `git mv` (histórico preservado). Origem → destino.

## Auditorias

| Origem | Destino |
|--------|---------|
| `docs/auditoria-pos-implementacao/` (14 itens) | `docs/audits/current/` |
| `docs/auditoria-capitulo-5/` (22 itens, inclui `final/` e `requirements_map.yaml`) | `docs/audits/archive/2026-08-03-capitulo-5/` |

## ADRs e arquitetura

| Origem | Destino |
|--------|---------|
| `docs/decisions/ADR-00{1,2,3}-*.md` | `docs/architecture/decisions/` |
| `docs/architecture/pipeline.md` | `docs/architecture/data-lifecycle.md` |
| `docs/architecture/components.md` | `docs/architecture/component-responsibilities.md` |
| `docs/domain/statuses-and-events.md` | `docs/architecture/result-state-model.md` |

## Operação/testes → development

| Origem | Destino |
|--------|---------|
| `docs/operations/running-the-prototype.md` | `docs/development/setup.md` |
| `docs/operations/configuration.md` | `docs/development/configuration.md` |
| `docs/operations/reset-and-seed.md` | `docs/development/reset-and-seed.md` |
| `docs/testing/test-scenarios.md` | `docs/development/testing.md` |

## Evidências e prompts

| Origem | Destino |
|--------|---------|
| `IMPLEMENTACAO_ETHEREUM_SEPOLIA.md` (raiz) | `docs/evidence/blockchain/` |
| `agrotrace-carbon-model-training-service/CURSOR_PROMPT.md` | `docs/archive/prompts/model-training-CURSOR_PROMPT.md` |

## Referências atualizadas após mover

- `frontend/scripts/generate_audit_reports.py` e `run_full_regression.py` (caminhos padrão).
- Docstrings: `frontend/utils/{global_filter,store_schemas,temporal_model}.py`, `frontend/services/page_context.py`.
- Regras Cursor: `00-project-overview`, `08-documentation`, `09-frontend-structure`.

Diretórios `docs/operations/`, `docs/testing/`, `docs/decisions/` ficaram vazios após
os `git mv` e foram removidos do disco (não versionados). `docs/domain/` mantém
`calculations.md` e `temporal-and-organizational-granularity.md`.
