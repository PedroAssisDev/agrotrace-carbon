# 01 — Matriz de contratos

| Consumidor | Fornecedor | Contrato | Versão requerida | Teste |
|---|---|---|---|---|
| frontend | save-file | `save_original_*` / `retrieve_original` | 1.0.0 | unittest save-file + adapter tests |
| frontend | wrappers | `process_file` + `detect_layout_id` | 1.0.0 | pytest wrappers + pipeline smoke |
| frontend | ontology | populate / validate / publish | 1.0.0 | pytest ontology + validate_ontology_* |
| frontend | calculation | `compute_farm_period_emissions` | 1.0.0 | pytest calculation + validate_preliminary_* |
| frontend | model-training | `ModelTrainingFacade` (consulta) | 1.0.0 | pytest model-training + validate_prediction_separation |
| frontend | traceability | `ProvenanceRecorder` / UoW | 1.0.0 | pytest traceability + provenance validators |
| frontend | blockchain | evidence / Merkle / anchor (pós-gate) | 1.0.0 | pytest blockchain (sem Sepolia) + full cycle |
