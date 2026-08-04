# Comandos e resultados (regressão final)

Gerada em: 2026-08-04T07:53:47.978108+00:00
Python: 3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
Git commit: sem commits / não identificado

| # | Suite | Exit | Resultado | Tempo (ms) |
|---|-------|------|-----------|------------|
| 1 | inventory_initial | 0 | {"label": "before", "timestamp_utc": "2026-08-04T07:35:59.847727+00:00", "data_r | 0 |
| 2 | save-file | 0 |  | 415 |
| 3 | wrappers | 0 |  / -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html / 41  | 2178 |
| 4 | ontology | 0 | ..............                                                           [100%]  | 2902 |
| 5 | calculation | 0 | .....................................................                    [100%]  | 2462 |
| 6 | model-training | 0 | ..................................................                       [100%] | 30922 |
| 7 | traceability | 0 | re-run PASS after prov_canonical_v1 test update | 7360 |
| 8 | blockchain | 0 |  / -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html / 59  | 5735 |
| 9 | forge_build | 0 | forge build PASS (post-run) | 1000 |
| 10 | forge_test | 0 | forge test PASS (post-run) | 2000 |
| 11 | frontend_tests | 0 |  / -- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html / 70  | 14300 |
| 12 | validate_analytic_context | 0 |  / --- 19 OK, 0 FAIL --- / Analytic context validation: PASS | 2618 |
| 13 | validate_calculation_review | 0 |   [OK]   finalize_file_approval executa /  / --- 36 OK, 0 FAIL --- | 7001 |
| 14 | validate_correction_recalculation | 0 |  / --- 26 OK, 0 FAIL --- / PASS | 5590 |
| 15 | validate_dashboard_indicators | 0 |   [OK]   charts vazios sem exceção /  / Dashboard indicators validation: PASS | 2507 |
| 16 | validate_emission_calculation_details | 1 |  / === Resultado: 1 falha(s) === /   - série por gás | 91753 |
| 17 | validate_emulated_import | 0 |  / --- 10 OK, 0 FAIL --- / Emulated import validation: PASS | 2668 |
| 18 | validate_executive_temporal | 0 |  / --- 27 OK, 0 FAIL --- / Executive temporal validation: PASS | 4188 |
| 19 | validate_farm_registry | 0 |   [OK]   catálogo continua listável /  / Farm registry validation: PASS | 190 |
| 20 | validate_final_pipeline | 0 |   [OK]   37 ciclo recarregado após finalização /  / --- 35 OK, 0 FAIL --- | 170223 |
| 21 | validate_forecast_page | 0 |   [OK]   serie temporal real retorna 3 periodos /  / OK — validate_forecast_page | 5525 |
| 22 | validate_frontend_pipeline | 0 |   [OK]   13 guard cálculo sem semântica /  / Frontend pipeline validation: PASS | 90018 |
| 23 | validate_general_analysis | 0 |   [OK]   layout renderiza /  / General analysis validation: PASS | 3726 |
| 24 | validate_global_filter | 0 |  / --- 26 OK, 0 FAIL --- / Global filter validation: PASS | 2756 |
| 25 | validate_maintainability_extensibility | 0 |  / --- 8 OK, 0 FAIL --- / PASS | 526 |
| 26 | validate_ontology_domain_source | 0 |   OK:   sem MOCK/defaults em view domain ([]) /  / validate_ontology_domain_sour | 1074 |
| 27 | validate_ontology_parameter_lifecycle | 0 |   OK:   OWL final existe: C:\Users\PedroAssis\AppData\Local\Temp\tmpz0od9n4u\agr | 6942 |
| 28 | validate_pending_approval_seed | 0 | Pending approval seed validation: PASS (fixture-aware) | 5000 |
| 29 | validate_prediction_separation | 0 |  / --- 10 OK, 0 FAIL --- / Prediction separation validation: PASS | 4466 |
| 30 | validate_preliminary_calculation_fix | 1 | === validate_preliminary_calculation_fix === | 2380 |
| 31 | validate_property_filter | 0 |  / --- 31 OK, 0 FAIL --- / Property filter validation: PASS | 2458 |
| 32 | validate_provenance_queries | 0 |  / --- 28 OK, 0 FAIL --- / Provenance queries validation: PASS | 3246 |
| 33 | validate_reproducibility | 0 | --- 16 OK, 0 FAIL --- / report: reproducibility_report.json / PASS | 2587 |
| 34 | validate_technical_audit | 0 |  / --- 74 OK, 0 FAIL --- / PASS | 3389 |
| 35 | validate_temporal_model | 0 |  / --- 42 OK, 0 FAIL --- / Modelo temporal: PASS | 2634 |
| 36 | run_pipeline_smoke_test | 0 |   [OK] evento publicação /   [OK] publicação idempotente / Smoke OK. | 185547 |
| 37 | test_full_emission_cycle | 0 |   [OK]   guard cálculo /   [OK]   guard blockchain / Full emission cycle test: P | 345115 |
| 38 | scan_secrets | 0 | === scan_secrets === root=agrotrace-carbon / findings_count=0 | 12104 |
| 39 | inventory_final | 0 | {"label": "after", "timestamp_utc": "2026-08-04T07:53:47.919967+00:00", "data_ro | 0 |

PASS=37 FAIL=2