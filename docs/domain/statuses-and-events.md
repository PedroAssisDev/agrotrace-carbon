# Status e eventos

Fonte de vocabulário no frontend: `frontend/services/domain_catalog.py` (+ `cycle_state` / `pipeline_display` para etapas).

Eventos canônicos principais (emissão única por fato):

- `RAW_DATA_UPLOADED`, `WRAPPER_EXECUTED`, `NORMALIZED_BATCH_CREATED`
- `SEMANTIC_MAPPING_COMPLETED`, `SEMANTIC_VALIDATION_COMPLETED`
- `CALCULATION_PRELIMINARY_RESULT_CREATED`
- `CALCULATION_APPROVED` / `CALCULATION_REJECTED` / `CYCLE_APPROVED`
- `APPROVED_RESULT_PUBLISHED` (alias de leitura: `FINAL_ONTOLOGY_PUBLISHED`)
- `EVIDENCE_PACKAGE_CREATED`, `BLOCKCHAIN_ANCHORED`, `INTEGRITY_VERIFIED`
- `PIPELINE_STEP_FAILED`

Aliases legados são aceitos na leitura e não devem ser reemitidos.
