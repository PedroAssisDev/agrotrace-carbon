# Provenance Integration

## Initial strategy

MVP uses read-only SQLite access to provenance database via:

- `SQLiteProvenanceEventReader`
- `SQLiteProvenanceDataReader`

## Tables read

- `audit_outbox_event`
- `reporting_period`
- `pipeline_pipeline_run`
- `calculation_calculation_result_set`
- `calculation_calculation_execution`
- `calculation_result_aggregation_link`
- `audit_hash_record`

## Eligible events

- `CALCULATION_APPROVED`
- `MONTHLY_RESULT_CONSOLIDATED`
- `ANNUAL_RESULT_CONSOLIDATED`
- `APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY`
- `DAILY_DATA_AGGREGATED_TO_MONTHLY`
- `MONTHLY_DATA_AGGREGATED_TO_ANNUAL`

## Future adapters

- `HttpProvenanceClient`

## Rules

- Prefer structured FK columns over payload parsing
- Never mutate provenance data
- Never approve results or publish ontology from blockchain-service
