# Módulo: frontend (Dash)

## Visão geral

Interface e orquestrador visual do protótipo. Apresenta o ciclo de vida do dado e
coordena a execução das etapas chamando os serviços por import Python direto.

**Posição:** ponto de entrada do monorepo (`frontend/main.py`). Não implementa fórmulas,
wrappers, ontologia, ledger ou ancoragem — delega via adapters.

## Responsabilidades

- Renderizar as 8 rotas canônicas e a auditoria técnica (9 abas).
- Orquestrar a pipeline operacional (`local_orchestrator`) e apresentar o stepper visual.
- Integrar serviços via `services/*_adapter.py` (falha de import explícita; sem mock
  silencioso no runtime normal).
- Publicar manifesto final (`publication_service`) e aplicar o gate blockchain na UI.

## Não faz

- Não implementa regra de negócio dos serviços.
- Não usa HTTP para integrar módulos locais.
- Não executa ação de blockchain antes de `FINAL_ONTOLOGY_PUBLISHED`.
- Não redireciona rotas legadas (paths desconhecidos caem no Painel Executivo).

## Estrutura e símbolos

| Peça | Caminho |
|------|---------|
| Entrypoint | `frontend/main.py` (não use `app.py`) |
| Rotas | `frontend/pages/router.py` (`ROUTES`) |
| Sidebar | `frontend/layout/sidebar.py` |
| Orquestração | `services/local_orchestrator.py` |
| Estado (11 etapas) | `services/cycle_state.py` (`PIPELINE_STEP_DEFS`) |
| Stepper (18 + AUDIT) | `services/pipeline_display.py` |
| Adapters | `services/*_adapter.py`, `direct_imports.py` |
| View services | `*_view_service.py`, `dashboard_service.py` |
| Filtro global | `utils/global_filter.py`, `services/page_context.py` |

## Rotas (8)

| Rota | Label na sidebar | Página |
|------|------------------|--------|
| `/` | Painel Executivo | `dashboard.py` |
| `/data-entry` | Entrada de Dados | `data_entry.py` |
| `/calculations` | Cálculos de Emissão | `emission_calculations.py` |
| `/approval` | Revisão e Aprovação | `approval_review.py` |
| `/indicators` | Análise Geral | `sustainability_indicators.py` |
| `/previsoes` | Previsões | `forecasts.py` |
| `/technical-audit` | Auditoria Técnica (9 abas) | `technical_audit.py` |
| `/settings` | Configurações | `settings.py` |

Blockchain e evidências ficam na aba de blockchain de `/technical-audit` (não há rota
`/blockchain`). Paths antigos **não** são redirecionados.

### Previsões (`/previsoes`)

Separadas do ciclo MRV oficial: treinamento via `model_training_adapter` →
`ModelTrainingFacade`; inferência em `services/forecast_inference/`. Publicação oficial
rejeita payloads de predição (`publication_service`).

## Filtro global (analítico vs operacional)

- **Analítico (navbar):** `farm_id`, `analysis_period_start/end`, `view_granularity`;
  KPIs/gráficos usam `cycles_for_analysis()`.
- **Operacional (local):** `cycle_id`; proveniência, evidências, wizard.
- Campos legados (`property_ids`, `period_mode`) apenas em compatibilidade de leitura.

## Persistência e ambiente

- Ciclos: `$AGROTRACE_DATA_ROOT/cycles/*.json`
- Propriedades: `$AGROTRACE_DATA_ROOT/properties/`
- SQLite: `$AGROTRACE_DATA_ROOT/db/` (bootstrap)
- Env (nomes): `AGROTRACE_DATA_ROOT`, `AGROTRACE_LOG_LEVEL`, `AGROTRACE_LOG_FILE`
- Flags: `USE_DIRECT_FUNCTION_CALLS`, `USE_MOCK_DATA`, `ALLOW_MOCK_FALLBACK` (`config.py`)

## Funcionalidades implementadas (evidência)

| Funcionalidade | Implementado em |
|----------------|-----------------|
| Bootstrap + paths + SQLite | `services/bootstrap.py` |
| Pipeline 11 etapas | `local_orchestrator.py`, `cycle_state.py` |
| Gate blockchain | `blockchain_view_service.is_blockchain_unlocked`, `pipeline_guards.py` |
| Publicação | `publication_service.py` |
| Seed demo | `scripts/reset_and_seed_pending_cycles.py` |
| Regressão | `scripts/run_full_regression.py` |

## Testes e comandos

```bash
cd frontend
python main.py
pytest
python scripts/run_pipeline_smoke_test.py
python scripts/test_full_emission_cycle.py
python scripts/run_full_regression.py
```

Seed canônico e aprovação em massa: [../development/reset-and-seed.md](../development/reset-and-seed.md).

## Limitações

- Sem redirects de URLs legadas.
- Forecasts dependem de artefatos treinados.
- Ancoragem default simulada (provider EVM opcional via env).

## Relacionados

- RF001, RF012–RF016, RF020; RNF002, RNF007.
- ADRs: [ADR-001](../architecture/decisions/ADR-001-frontend-as-interface-and-orchestrator.md),
  [ADR-002](../architecture/decisions/ADR-002-in-process-modular-integration.md).
- Detalhe operacional: [`frontend/README.md`](../../frontend/README.md).
