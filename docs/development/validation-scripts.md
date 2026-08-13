# Scripts de validação

Os scripts `frontend/scripts/validate_*.py` verificam comportamentos específicos da
pipeline e da UI. São executados em bloco pelo runner de regressão
(`run_full_regression.py`) e podem ser rodados isoladamente com `--data-root <dir>`.

## Grupos (arquivos existentes)

| Grupo | Scripts |
|-------|---------|
| Pipeline / ciclo | `validate_frontend_pipeline`, `validate_final_pipeline`, `validate_emulated_import`, `validate_correction_recalculation`, `validate_reproducibility` |
| Cálculo | `validate_calculation_review`, `validate_preliminary_calculation_form`, `validate_emission_calculation_details` |
| Filtros / temporal | `validate_global_filter`, `validate_property_filter`, `validate_temporal_model`, `validate_executive_temporal`, `validate_analytic_context` |
| Indicadores / dashboard | `validate_dashboard_indicators`, `validate_general_analysis` |
| Ontologia / proveniência | `validate_ontology_domain_source`, `validate_ontology_parameter_lifecycle`, `validate_provenance_queries` |
| Previsão | `validate_forecast_page`, `validate_prediction_separation` |
| Auditoria / registro | `validate_technical_audit`, `validate_farm_registry`, `validate_pending_approval_seed` |
| Qualidade / requisitos | `validate_maintainability_extensibility`, `validate_requirements_ids` |

Há **25** scripts `validate_*.py` no repositório. Não existe
`validate_preliminary_calculation_view.py` — use `validate_preliminary_calculation_form.py`.

## Comandos conhecidos (referência rápida)

```bash
cd frontend
python scripts/run_pipeline_smoke_test.py
python scripts/test_full_emission_cycle.py
python scripts/validate_global_filter.py
python scripts/validate_property_filter.py
python scripts/validate_dashboard_indicators.py
```

Falhas conhecidas devem ser documentadas na auditoria atual (`docs/audits/current/`),
não silenciadas.
