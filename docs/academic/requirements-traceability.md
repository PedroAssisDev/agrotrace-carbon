# Rastreabilidade de requisitos

Relaciona cada requisito ao módulo, ao código, ao teste e ao cenário de avaliação. O
**estado de atendimento** não é reproduzido aqui como permanente: consulte a
[auditoria atual](../audits/current/00-resumo-executivo.md) para o status vigente e suas
limitações declaradas.

Mapeamento derivado de `docs/audits/current/09-resultados.json`.

| RF | Módulo | Código (exemplos) | Teste/validação | Cenário |
|----|--------|-------------------|-----------------|---------|
| RF001 | frontend / save-file | `pages/data_entry.py`, `save_file_adapter` | `run_pipeline_smoke_test` | CE1 |
| RF002 | save-file | `save_file/storage.py::retrieve_original` | `validate_technical_audit` | CE1 |
| RF003 | wrappers | `agrotrace-carbon-wrappers-service` | `validate_frontend_pipeline` | CE1 |
| RF004 | wrappers / ontology | validação de wrappers | wrappers + ontology tests | CE1 |
| RF005 | frontend / ontology | `domain_catalog.py`, `ontology/schema.py` | `validate_temporal_model` | CE1 |
| RF006 | traceability | `provenance_adapter`, `ProvenanceRecorder` | `validate_provenance_queries` | CE1/CE4 |
| RF007 | ontology-manager | `ontology-manager` | `validate_ontology_*` | CE1 |
| RF008 | calculation | `calculation_adapter` | `test_full_emission_cycle` | CE2 |
| RF009 | calculation | `emissions/explanation.py` | `test_calculation_explanation` | CE2 |
| RF010 | frontend | `result_correction_service.py` | `validate_correction_recalculation` | CE2 |
| RF011 | model-training | `publication_service._reject_prediction_input` | `validate_prediction_separation` | CE3 |
| RF012 | frontend | `indicator_service`, dashboard | `validate_dashboard_indicators` | CE5 |
| RF013 | frontend | `calculation_approval_service` | `validate_calculation_review` | CE2 |
| RF014 | frontend | `calculation_approval_service`, `result_correction_service` | `validate_calculation_review` | CE2 |
| RF015 | frontend | `calculation_approval_service` | `validate_pending_approval_seed` | CE2 |
| RF016 | frontend / ontology | `publication_service` | `test_full_emission_cycle` | CE2 |
| RF017 | blockchain | `evidence_package_builder` | `test_full_emission_cycle` | CE4 |
| RF018 | blockchain | `canonical_json_service`, `hash_helpers` | `validate_reproducibility` | CE4 |
| RF019 | blockchain | `CarbonEvidenceRegistry`, `SimulatedAnchorProvider` | forge + blockchain tests | CE4 |
| RF020 | frontend | `technical_audit.py`, callbacks | `validate_technical_audit` | CE5 |
| RF021 | blockchain / frontend | `blockchain_adapter`, `integrity_view_service` | full cycle + integrity | CE4 |

| RNF | Área | Evidência (exemplos) |
|-----|------|----------------------|
| RNF001 Rastreabilidade | proveniência | `validate_provenance_queries` + full cycle |
| RNF002 Auditabilidade | UI/adapters | `validate_technical_audit` |
| RNF003 Manutenibilidade | arquitetura | `validate_maintainability_extensibility` |
| RNF004 Integridade | canonical/verificação | `validate_reproducibility` |
| RNF005 Explicabilidade | explanation | `calc_explanation_v1` |
| RNF006 Consistência semântica | catálogo/OWL | `validate_temporal_model` |
| RNF007 Operabilidade | 8 rotas Dash | `validate_technical_audit`, forecast/approval |
| RNF008 Extensibilidade | registries/ports | `validate_maintainability_extensibility` |
| RNF009 Reprodutibilidade | canonical | `validate_reproducibility` |
| RNF010 Versionamento | `version_manifest_service.py` | testes do frontend |
| RNF011 Interoperabilidade | schemas/ABI | blockchain + forge |
| RNF012 Proteção de credenciais | `scan_secrets.py` | `scan_secrets` |

Limitações conhecidas (declaradas na auditoria, não resolvidas por esta reorganização):
classe `Lot` ausente na OWL (RF005/RNF006 parciais); dois `validate_*` de cálculo/detalhe
falhando (RF008/RF009/RNF005); Sepolia não reexecutada na última auditoria (RF019 com
evidência documental).
