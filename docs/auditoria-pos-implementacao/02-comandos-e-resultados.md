# Comandos e resultados

Fonte: `_regressao.json` gerado em 2026-08-04T13:27:52.171860+00:00

**Pass:** 37 | **Fail:** 2 | **Steps:** 39 | **Duração total:** 1419009 ms

| # | Nome | Exit | Duração (ms) | Resumo |
|---|------|------|--------------|--------|
| 1 | inventory_initial | 0 | 0 | {"label": "before", "timestamp_utc": "2026-08-04T13:04:13.066510+00:00", "data_root_name": "agrotrace-data", "cycle_coun |
| 2 | save-file | 0 | 986 |  |
| 3 | wrappers | 0 | 6480 |  / -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html / 41 passed, 3 skipped, 2 warnings in 1.87s |
| 4 | ontology | 0 | 8321 | ..............                                                           [100%] / 14 passed in 2.75s |
| 5 | calculation | 0 | 5572 | .....................................................                    [100%] / 53 passed in 1.64s |
| 6 | model-training | 0 | 83636 | ..................................................                       [100%] |
| 7 | traceability | 0 | 47750 |  / -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html / 115 passed, 1 warning in 43.95s |
| 8 | blockchain | 0 | 8926 |  / -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html / 59 passed, 4 deselected, 1 warning in 5.73s |
| 9 | forge_build | 0 | 2614 | No files changed, compilation skipped |
| 10 | forge_test | 0 | 2177 | Suite result: ok. 9 passed; 0 failed; 0 skipped; finished in 42.04ms (68.17ms CPU time) /  / Ran 1 test suite in 67.55ms |
| 11 | frontend_tests | 0 | 21981 |  / -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html / 70 passed, 32 warnings in 14.33s |
| 12 | validate_analytic_context | 0 | 4055 |  / --- 19 OK, 0 FAIL --- / Analytic context validation: PASS |
| 13 | validate_calculation_review | 0 | 9874 |   [OK]   finalize_file_approval executa /  / --- 36 OK, 0 FAIL --- |
| 14 | validate_correction_recalculation | 0 | 6781 |  / --- 26 OK, 0 FAIL --- / PASS |
| 15 | validate_dashboard_indicators | 0 | 3727 |   [OK]   charts vazios sem exceção /  / Dashboard indicators validation: PASS |
| 16 | validate_emission_calculation_details | 1 | 127030 |  / === Resultado: 1 falha(s) === /   - série por gás |
| 17 | validate_emulated_import | 0 | 2619 |  / --- 10 OK, 0 FAIL --- / Emulated import validation: PASS |
| 18 | validate_executive_temporal | 0 | 5032 |  / --- 27 OK, 0 FAIL --- / Executive temporal validation: PASS |
| 19 | validate_farm_registry | 0 | 183 |   [OK]   catálogo continua listável /  / Farm registry validation: PASS |
| 20 | validate_final_pipeline | 0 | 215286 |   [OK]   37 ciclo recarregado após finalização /  / --- 35 OK, 0 FAIL --- |
| 21 | validate_forecast_page | 0 | 7881 |   [OK]   serie temporal real retorna 3 periodos /  / OK — validate_forecast_page |
| 22 | validate_frontend_pipeline | 0 | 142352 |   [OK]   13 guard cálculo sem semântica /  / Frontend pipeline validation: PASS |
| 23 | validate_general_analysis | 0 | 6289 |   [OK]   layout renderiza /  / General analysis validation: PASS |
| 24 | validate_global_filter | 0 | 4228 |  / --- 26 OK, 0 FAIL --- / Global filter validation: PASS |
| 25 | validate_maintainability_extensibility | 0 | 589 |  / --- 8 OK, 0 FAIL --- / PASS |
| 26 | validate_ontology_domain_source | 0 | 1321 |   OK:   sem MOCK/defaults em view domain ([]) /  / validate_ontology_domain_source OK |
| 27 | validate_ontology_parameter_lifecycle | 0 | 11363 |   OK:   OWL final existe: C:\Users\PedroAssis\AppData\Local\Temp\tmp8ler55do\agrotrace-data\ontology_exports\TEST-ONTO-L |
| 28 | validate_pending_approval_seed | 0 | 4635 |  / --- 18 OK, 0 FAIL --- / Pending approval seed validation: PASS |
| 29 | validate_prediction_separation | 0 | 12088 |  / --- 10 OK, 0 FAIL --- / Prediction separation validation: PASS |
| 30 | validate_preliminary_calculation_fix | 1 | 4084 | === validate_preliminary_calculation_fix === |
| 31 | validate_property_filter | 0 | 4089 |  / --- 31 OK, 0 FAIL --- / Property filter validation: PASS |
| 32 | validate_provenance_queries | 0 | 4056 |  / --- 28 OK, 0 FAIL --- / Provenance queries validation: PASS |
| 33 | validate_reproducibility | 0 | 2699 | --- 16 OK, 0 FAIL --- / report: reproducibility_report.json / PASS |
| 34 | validate_technical_audit | 0 | 3922 |  / --- 74 OK, 0 FAIL --- / PASS |
| 35 | validate_temporal_model | 0 | 2778 |  / --- 42 OK, 0 FAIL --- / Modelo temporal: PASS |
| 36 | run_pipeline_smoke_test | 0 | 270822 |   [OK] evento publicação /   [OK] publicação idempotente / Smoke OK. |
| 37 | test_full_emission_cycle | 0 | 357670 |   [OK]   guard cálculo /   [OK]   guard blockchain / Full emission cycle test: PASS |
| 38 | scan_secrets | 0 | 15113 | === scan_secrets === root=agrotrace-carbon / findings_count=0 |
| 39 | inventory_final | 0 | 0 | {"label": "after", "timestamp_utc": "2026-08-04T13:27:52.122292+00:00", "data_root_name": "agrotrace-data", "cycle_count |

## Falhas

### validate_emission_calculation_details
- comando: `C:\Users\PedroAssis\Documents\agrotrace-carbon\.venv\Scripts\python.exe C:\Users\PedroAssis\Documents\agrotrace-carbon\frontend\scripts\validate_emission_calculation_details.py --data-root C:\Users\PEDROA~1\AppData\Local\Temp\tmp8ler55do\agrotrace-data`
- cwd: `C:\Users\PedroAssis\Documents\agrotrace-carbon\frontend`
- summary:  | === Resultado: 1 falha(s) === |   - série por gás
- stderr_tail:
```

```

### validate_preliminary_calculation_fix
- comando: `C:\Users\PedroAssis\Documents\agrotrace-carbon\.venv\Scripts\python.exe C:\Users\PedroAssis\Documents\agrotrace-carbon\frontend\scripts\validate_preliminary_calculation_fix.py --data-root C:\Users\PEDROA~1\AppData\Local\Temp\tmp8ler55do\agrotrace-data`
- cwd: `C:\Users\PedroAssis\Documents\agrotrace-carbon\frontend`
- summary: === validate_preliminary_calculation_fix ===
- stderr_tail:
```
talog)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:/Users/PedroAssis/Documents/agrotrace-carbon/frontend/services/calculation_adapter.py", line 557, in _resolve_factors
    raise RuntimeError(
RuntimeError: Parâmetros obrigatórios ausentes na ontologia (factor_catalog): enteric_ch4_kg_per_animal, manure_kg_per_kg_bw_per_day, manure_ch4_kg_per_kg_manure, energy_co2_kg_per_unit, fertilizer_factors, gwp. Insira defaults como pending antes do cálculo.

```


## Observações

- Nenhuma transação Sepolia enviada.
- `reset_test_environment.py` não executado.
- Ambiente: `AGROTRACE_DATA_ROOT` sob TemporaryDirectory do runner.
- Skips conhecidos: wrappers 3 skipped; blockchain 4 deselected (`blockchain_local`/`sepolia`).
