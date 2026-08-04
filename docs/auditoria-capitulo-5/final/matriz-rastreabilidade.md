# Matriz de rastreabilidade (recomputada)

Gerada em: 2026-08-04T07:58:23.848945+00:00

Legenda: A=Atendido · P=Parcial · N=Não atendido · NV=Não verificável

## Contagens por grupo (não agregadas)

### RF (total=21)

| Status | Qtd |
|--------|-----|
| A | 17 |
| P | 4 |
| N | 0 |
| NV | 0 |
| NA | 0 |

### RNF (total=12)

| Status | Qtd |
|--------|-----|
| A | 12 |
| P | 0 |
| N | 0 |
| NV | 0 |
| NA | 0 |

### RN (total=10)

| Status | Qtd |
|--------|-----|
| A | 10 |
| P | 0 |
| N | 0 |
| NV | 0 |
| NA | 0 |

### CE (total=5)

| Status | Qtd |
|--------|-----|
| A | 4 |
| P | 1 |
| N | 0 |
| NV | 0 |
| NA | 0 |

## RF

| ID | Requisito | Status | Confiança | Evidência estática | Teste executado | Evidência visual | Limitação |
|----|-----------|--------|-----------|--------------------|-----------------|------------------|-----------|
| RF001 | Ingestão de dados brutos | A | alta | frontend/services/save_file_adapter.py | save-file, validate_frontend_pipeline, run_pipeline_smoke_test | Upload na UI | — |
| RF002 | Recuperação do bruto | A | alta | agrotrace-carbon-save-file/save_file/__init__.py | save-file, validate_technical_audit | Aba Artefatos | — |
| RF003 | Normalização via wrappers | A | alta | agrotrace-carbon-wrappers-service | wrappers, validate_frontend_pipeline | — | — |
| RF004 | Ontologia semântica | A | alta | agrotrace-carbon-ontology-manager | ontology, validate_ontology_domain_source | — | — |
| RF005 | Granularidades temporal/organizacional | P | média | frontend/utils/temporal_model.py | validate_temporal_model, seed_test_scenarios | Filtro temporal | ver comandos-e-resultados / falhas declaradas |
| RF006 | Cálculo preliminar | P | média | agrotrace-carbon-calculation-service | calculation, validate_emission_calculation_details | — | ver comandos-e-resultados / falhas declaradas |
| RF007 | Revisão e aprovação | A | alta | frontend/services/calculation_approval_service.py | validate_calculation_review, validate_pending_approval_seed | /approval | — |
| RF008 | Publicação final | A | alta | frontend/services/publication_service.py | test_full_emission_cycle, validate_ontology_parameter_lifecycle | — | — |
| RF009 | Fatores e GWP | P | média | agrotrace-carbon-calculation-service/emissions | calculation, validate_emission_calculation_details | — | ver comandos-e-resultados / falhas declaradas |
| RF010 | Correção e recálculo | A | alta | frontend/services/calculation_approval_service.py | validate_correction_recalculation | — | — |
| RF011 | Separação cálculo/predição | A | alta | frontend/services/forecast_inference | validate_prediction_separation, validate_forecast_page | /forecasts | — |
| RF012 | Pacote de evidências | A | alta | agrotrace-carbon-blockchain-service | blockchain, test_full_emission_cycle | — | — |
| RF013 | Hash e Merkle | P | média | app/domain/services/sha256_service.py | blockchain, validate_reproducibility, test_canonical_vectors | — | ver comandos-e-resultados / falhas declaradas |
| RF014 | Ancoragem | A | alta | agrotrace-carbon-blockchain-service/app/application/use_cases | blockchain, test_full_emission_cycle | — | — |
| RF015 | Verificação de integridade | A | alta | verify_evidence_package.py | blockchain, validate_technical_audit | Aba Integridade | — |
| RF016 | Proveniência contínua | A | alta | agrotrace-carbon-traceability-service | traceability, validate_provenance_queries | Aba Proveniência | — |
| RF017 | Dashboard indicadores | A | alta | frontend/services/dashboard_service.py | validate_dashboard_indicators, validate_executive_temporal | / | — |
| RF018 | Canonicalização determinística | A | alta | canonical_json_service.py | blockchain, validate_reproducibility, frontend_tests | — | — |
| RF019 | Filtros analíticos | A | alta | frontend/utils/global_filter.py | validate_global_filter, validate_property_filter, validate_analytic_context | Filtro global | — |
| RF020 | Auditoria técnica | A | alta | frontend/pages/technical_audit.py | validate_technical_audit | /technical-audit | — |
| RF021 | Previsões | A | alta | frontend/pages/forecasts.py | validate_forecast_page, model-training | /forecasts | — |

## RNF

| ID | Requisito | Status | Confiança | Evidência estática | Teste executado | Evidência visual | Limitação |
|----|-----------|--------|-----------|--------------------|-----------------|------------------|-----------|
| RNF001 | Rastreabilidade ponta a ponta | A | alta | provenance + blockchain adapters | traceability, blockchain, test_full_emission_cycle | Trilha auditoria | — |
| RNF002 | Usabilidade auditoria | A | alta | technical_audit | validate_technical_audit | 9 abas | — |
| RNF003 | Manutenibilidade | A | alta | LayoutRegistry | validate_maintainability_extensibility | — | — |
| RNF004 | Integridade criptográfica | A | alta | json_canonical_v1 | blockchain, validate_reproducibility, scan_secrets | — | — |
| RNF005 | Transparência metodológica | A | alta | VersionManifest | frontend_tests, validate_technical_audit | VersionManifest na auditoria | — |
| RNF006 | Modelo temporal | A | alta | temporal_model.py | validate_temporal_model | — | — |
| RNF007 | Performance UI aceitável | A | alta | technical_audit Loading | validate_technical_audit | — | — |
| RNF008 | Extensibilidade providers | A | alta | BlockchainAnchorProviderPort | validate_maintainability_extensibility | — | — |
| RNF009 | Reprodutibilidade | A | alta | validate_reproducibility.py | validate_reproducibility | — | — |
| RNF010 | Versionamento | A | alta | version_manifest_service.py | frontend_tests, blockchain | — | — |
| RNF011 | Conformidade de schema | A | alta | test_anchor_payload_schema.py | blockchain | — | — |
| RNF012 | Proteção de credenciais | A | alta | app/shared/redact.py | scan_secrets, frontend_tests | — | — |

## RN

| ID | Requisito | Status | Confiança | Evidência estática | Teste executado | Evidência visual | Limitação |
|----|-----------|--------|-----------|--------------------|-----------------|------------------|-----------|
| RN-01 | Integração direta sem HTTP | A | alta | .cursor/rules/01-architecture-direct-calls.mdc | frontend_tests | — | — |
| RN-02 | Gate FINAL_ONTOLOGY_PUBLISHED | A | alta | blockchain_view_service.py | test_full_emission_cycle | — | — |
| RN-03 | Predição ≠ cálculo publicado | A | alta | publication_service.py | validate_prediction_separation | — | — |
| RN-04 | Append-only ledger | A | alta | sqlite_append_only.py | traceability, blockchain | — | — |
| RN-05 | Proveniência ≠ ancoragem | A | alta | docs/conceptual_model_mrv.md | validate_technical_audit | — | — |
| RN-06 | Sem fallback compact JSON oficial | A | alta | hash_helpers.py | frontend_tests, validate_reproducibility | — | — |
| RN-07 | Milestone de publicação | A | alta | publication_service.py | test_full_emission_cycle | — | — |
| RN-08 | Minimização on-chain | A | alta | evm_anchor_provider.py | blockchain | — | — |
| RN-09 | Filtro global vs operacional | A | alta | docs/filter_architecture_mrv.md | validate_global_filter | — | — |
| RN-10 | Entrypoint frontend/main.py | A | alta | frontend/main.py | frontend_tests | — | — |

## CE

| ID | Requisito | Status | Confiança | Evidência estática | Teste executado | Evidência visual | Limitação |
|----|-----------|--------|-----------|--------------------|-----------------|------------------|-----------|
| CE1 | Ciclo multi-granularidade | P | média | seed_test_scenarios.py | validate_temporal_model, seed_test_scenarios | — | ver comandos-e-resultados / falhas declaradas |
| CE2 | Aprovação humana | A | alta | approval_review.py | validate_calculation_review, validate_pending_approval_seed | — | — |
| CE3 | Evidência e verificação | A | alta | blockchain-service | test_full_emission_cycle, blockchain | — | — |
| CE4 | Proveniência até transação | A | alta | provenance + anchoring | traceability, validate_technical_audit | — | — |
| CE5 | Auditoria técnica | A | alta | /technical-audit | validate_technical_audit | 9 abas | — |
