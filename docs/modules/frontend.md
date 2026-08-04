# Módulo: frontend (Dash)

## Finalidade

Interface e orquestrador visual do protótipo. Apresenta o ciclo de vida do dado e
coordena a execução das etapas chamando os serviços por import Python direto.

## Responsabilidades

- Renderizar as 8 rotas canônicas e a auditoria técnica (9 abas).
- Orquestrar a pipeline operacional (`local_orchestrator`) e apresentar o stepper visual.
- Integrar serviços via `services/*_adapter.py` com fallback explícito de import.

## Não faz

- Não implementa regra de negócio dos serviços.
- Não usa HTTP para integrar módulos locais.
- Não executa ação de blockchain antes de `FINAL_ONTOLOGY_PUBLISHED`.

## Estrutura e símbolos

- Entrypoint: `frontend/main.py` (não use `app.py`).
- Rotas: `frontend/pages/router.py` (`ROUTES`, `LEGACY_REDIRECTS`).
- Orquestração: `services/local_orchestrator.py`; estado: `services/cycle_state.py`
  (`PIPELINE_STEP_DEFS`, 11 etapas); stepper: `services/pipeline_display.py`
  (`DISPLAY_PIPELINE_STEPS`, 18 etapas).
- View services: `*_view_service.py`, `dashboard_service.py`.
- Filtro global: `utils/global_filter.py`, `services/page_context.py`,
  `utils/store_schemas.py`, `utils/temporal_model.py`.

## Rotas (8)

`/`, `/data-entry`, `/calculations`, `/approval`, `/indicators`, `/previsoes`,
`/technical-audit`, `/settings`. Rotas antigas redirecionam via `LEGACY_REDIRECTS`.

## Filtro global (analítico vs operacional)

- **Analítico (navbar):** `farm_id`, `analysis_period_start/end`, `view_granularity`;
  KPIs/gráficos usam `cycles_for_analysis()`.
- **Operacional (local):** `cycle_id` (= `operational_cycle_id`); proveniência, evidências, wizard.
- Campos legados (`property_ids`, `period_mode`) apenas em compatibilidade de leitura.

## Persistência e ambiente

- Estado do ciclo em `AGROTRACE_DATA_ROOT/cycles/*.json`; SQLite sob `db/` (bootstrap).
- Env (nomes): `AGROTRACE_DATA_ROOT`, `AGROTRACE_LOG_LEVEL`, `AGROTRACE_LOG_FILE`.
- Flags: `USE_DIRECT_FUNCTION_CALLS`, `USE_MOCK_DATA`, `ALLOW_MOCK_FALLBACK` (`config.py`).

## Compatibilidade legada

Redirects de rotas antigas; alias `yearly`; `property_ids`/`period_mode`; fallback `mock_data.py`.

## Testes e comandos

- `python main.py` (UI); `pytest frontend/tests`; `validate_*.py`; `run_full_regression.py`.

## Relacionados

- RF001, RF012–RF016, RF020; RNF002, RNF007.
- ADRs: [ADR-001](../architecture/decisions/ADR-001-frontend-as-interface-and-orchestrator.md),
  [ADR-002](../architecture/decisions/ADR-002-in-process-modular-integration.md).
- Estrutura detalhada: `frontend/README.md`; ciclo: [../architecture/data-lifecycle.md](../architecture/data-lifecycle.md).
