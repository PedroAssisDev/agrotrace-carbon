# Scripts de validação

Os scripts `frontend/scripts/validate_*.py` verificam comportamentos específicos da
pipeline e da UI. São executados em bloco pelo runner de regressão
(`run_full_regression.py`) e podem ser rodados isoladamente com `--data-root <dir>`.

## Grupos

| Grupo | Scripts |
|-------|---------|
| Pipeline / ciclo | `validate_frontend_pipeline`, `validate_final_pipeline`, `validate_emulated_import`, `validate_correction_recalculation`, `validate_reproducibility` |
| Cálculo | `validate_calculation_review`, `validate_preliminary_calculation_form`, `validate_preliminary_calculation_view`, `validate_emission_calculation_details` |
| Filtros / temporal | `validate_global_filter`, `validate_property_filter`, `validate_temporal_model`, `validate_executive_temporal`, `validate_analytic_context` |
| Indicadores / dashboard | `validate_dashboard_indicators`, `validate_general_analysis` |
| Ontologia / proveniência | `validate_ontology_domain_source`, `validate_ontology_parameter_lifecycle`, `validate_provenance_queries` |
| Previsão | `validate_forecast_page`, `validate_prediction_separation` |
| Auditoria / registro | `validate_technical_audit`, `validate_farm_registry`, `validate_pending_approval_seed` |
| Qualidade | `validate_maintainability_extensibility` |

## Comandos conhecidos (referência rápida)

- `python scripts/run_pipeline_smoke_test.py` — smoke ponta a ponta.
- `python scripts/test_full_emission_cycle.py` — ciclo completo + gate blockchain.
- `python scripts/validate_global_filter.py` / `validate_property_filter.py` — filtros.
- `python scripts/validate_dashboard_indicators.py` — indicadores do dashboard.

Falhas pré-existentes conhecidas (não introduzidas pela reorganização) devem ser
documentadas na auditoria atual, não silenciadas.
