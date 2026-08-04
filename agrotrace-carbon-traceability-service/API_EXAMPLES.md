# API examples — end-to-end provenance flow

All examples assume the API is running on `http://localhost:8080`. UUID
values are illustrative — the API generates time-ordered UUID v7 internally.

## 1. Start a pipeline run

```bash
curl -X POST http://localhost:8080/api/v1/pipeline-runs \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: corr-001" \
  -d '{
    "run_code": "run-2026-04-29-001",
    "farm_reference": "farm-acre-7",
    "reporting_period_reference": "2026-Q1",
    "idempotency_key": "run-2026-04-29-001"
  }'
```

```json
{
  "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
  "run_code": "run-2026-04-29-001",
  "farm_reference": "farm-acre-7",
  "reporting_period_reference": "2026-Q1",
  "run_status": "running",
  "started_at": "2026-04-29T22:00:00.123456+00:00",
  "finished_at": null,
  "parent_pipeline_run_id": null,
  "triggered_by_agent_id": null,
  "tenant_id": null,
  "notes": null,
  "idempotency_key": "run-2026-04-29-001",
  "metadata": {}
}
```

## 2. Register the raw source artifact

```bash
curl -X POST http://localhost:8080/api/v1/source-artifacts \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
    "source_system": "ERP-XML",
    "original_filename": "milk-2026-04.xml",
    "storage_uri": "s3://agrotrace-raw/milk-2026-04.xml",
    "content_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    "source_layout_name": "erp-xml",
    "source_layout_version": "v3",
    "mime_type": "application/xml",
    "file_size_bytes": 18432,
    "idempotency_key": "src-milk-2026-04"
  }'
```

## 3. Register the wrapper definition (cache the wrapper code identity)

```bash
curl -X POST http://localhost:8080/api/v1/wrapper-definitions \
  -H "Content-Type: application/json" \
  -d '{
    "wrapper_name": "erp-xml-to-canonical",
    "wrapper_version": "1.4.0",
    "source_layout_name": "erp-xml",
    "source_layout_version": "v3",
    "schema_version": "canonical/1.0",
    "code_hash": "8b1a9953c4611296a827abf8c47804d7"
  }'
```

## 4. Record the wrapper execution

```bash
curl -X POST http://localhost:8080/api/v1/wrapper-executions \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
    "wrapper_definition_id": "<wrapper_definition_id>",
    "input_artifact_id": "<source_artifact_id>",
    "started_at": "2026-04-29T22:01:00+00:00",
    "finished_at": "2026-04-29T22:01:42+00:00",
    "warning_count": 0,
    "error_count": 0,
    "execution_status": "succeeded",
    "executor_agent_external_reference": "wrapper:erp-xml-to-canonical@1.4.0",
    "idempotency_key": "wexec-2026-04-29-001"
  }'
```

## 5. Register the normalized batch

```bash
curl -X POST http://localhost:8080/api/v1/normalized-batches \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
    "wrapper_execution_id": "<wrapper_execution_id>",
    "batch_code": "milk-canonical-2026-04",
    "schema_version": "canonical/1.0",
    "record_count": 2143,
    "storage_uri": "s3://agrotrace-canonical/milk-2026-04.parquet",
    "content_hash": "1b6453892473a467d07372d45eb05abc2031647a",
    "idempotency_key": "batch-milk-2026-04"
  }'
```

## 6. Record the semantic integration execution

```bash
curl -X POST http://localhost:8080/api/v1/semantic-integrations \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
    "normalized_batch_id": "<normalized_batch_id>",
    "ontology_name": "agrotrace-onto",
    "ontology_version": "2026.04",
    "mapping_rule_version": "1.2.0",
    "started_at": "2026-04-29T22:02:00+00:00",
    "finished_at": "2026-04-29T22:02:30+00:00",
    "triples_generated": 51234,
    "execution_status": "succeeded",
    "idempotency_key": "sem-int-milk-2026-04"
  }'
```

## 7. Publish a canonical snapshot

```bash
curl -X POST http://localhost:8080/api/v1/canonical-snapshots \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
    "semantic_integration_execution_id": "<semantic_integration_id>",
    "graph_name": "https://agrotrace.org/graph/milk/2026-Q1",
    "snapshot_label": "milk-2026-Q1-snapshot",
    "schema_version": "canonical/1.0",
    "storage_uri": "s3://agrotrace-canonical-snapshots/milk-2026-Q1.json",
    "items": [
      {"item_key": "farm:acre-7", "payload": {"animals": 122, "milk_kg": 432100}}
    ]
  }'
```

The response includes the deterministic `snapshot_hash` (SHA-256 over the
canonical payload).

## 8. Calculation method + version + parameters

```bash
curl -X POST http://localhost:8080/api/v1/calculation-methods \
  -H "Content-Type: application/json" \
  -d '{
    "method_code": "ipcc-2019-tier-2",
    "method_name": "IPCC 2019 Refinement — Tier 2 (dairy)"
  }'

curl -X POST http://localhost:8080/api/v1/calculation-method-versions \
  -H "Content-Type: application/json" \
  -d '{
    "calculation_method_id": "<method_id>",
    "version_label": "1.0.0",
    "status": "active",
    "implementation_version": "agrotrace-calc/2.3.1"
  }'

curl -X POST http://localhost:8080/api/v1/parameter-sets \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
    "calculation_method_version_id": "<method_version_id>",
    "values": [
      {"parameter_name": "ef_methane_dairy", "parameter_value_numeric": "117.5", "parameter_unit": "kgCH4/head/yr"},
      {"parameter_name": "gwp_ch4", "parameter_value_numeric": "28", "parameter_unit": "co2e_factor"}
    ]
  }'
```

## 9. Calculation execution + result set

```bash
curl -X POST http://localhost:8080/api/v1/calculation-executions \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
    "canonical_snapshot_id": "<snapshot_id>",
    "calculation_method_version_id": "<method_version_id>",
    "calculation_parameter_set_id": "<parameter_set_id>",
    "started_at": "2026-04-29T22:03:00+00:00",
    "finished_at": "2026-04-29T22:03:14+00:00",
    "execution_status": "succeeded",
    "idempotency_key": "calc-exec-milk-2026-04",
    "reporting_period_id": "<reporting_period_id>"
  }'

curl -X POST http://localhost:8080/api/v1/calculation-result-sets \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
    "calculation_execution_id": "<calculation_execution_id>",
    "result_set_status": "preliminary",
    "reporting_period_id": "<reporting_period_id>",
    "result_scope": "monthly",
    "consolidation_type": "direct",
    "items": [
      {
        "result_type": "emission_total",
        "result_name": "co2e_total",
        "result_value": "234567.89",
        "result_unit": "kgCO2e"
      },
      {
        "result_type": "intensity",
        "result_name": "co2e_per_kg_milk",
        "result_value": "0.84",
        "result_unit": "kgCO2e/kg"
      }
    ]
  }'

curl http://localhost:8080/api/v1/calculation-result-sets/<calculation_result_set_id>
```

## 10. Human review

```bash
curl -X POST http://localhost:8080/api/v1/calculation-reviews \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
    "calculation_result_set_id": "<calculation_result_set_id>",
    "reviewer_agent_id": "<existing_agent_id>",
    "decision": "approved",
    "review_comment": "Numbers match supplier-side audit"
  }'
```

## 11. Result publication (only when review is APPROVED)

```bash
curl -X POST http://localhost:8080/api/v1/result-publications \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
    "calculation_result_set_id": "<calculation_result_set_id>",
    "calculation_review_id": "<review_id>",
    "target_graph_name": "https://agrotrace.org/graph/published/milk/2026-Q1",
    "ontology_name": "agrotrace-onto",
    "ontology_version": "2026.04",
    "publication_status": "published",
    "ontology_uri": "urn:agrotrace:result:milk:2026-Q1:farm-acre-7",
    "rdf_class": "agro:CarbonResult"
  }'
```

## 12. Hash + blockchain anchor

```bash
curl -X POST http://localhost:8080/api/v1/hash-records \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
    "subject_kind": "bundle",
    "subject_id": "<bundle_id>",
    "hash_value": "fb1e7f6c9e8c52f3...",
    "hash_algorithm": "sha256"
  }'

curl -X POST http://localhost:8080/api/v1/blockchain-anchors \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_run_id": "018f4a91-3a1c-7c0e-a18d-2c4e8f0c0001",
    "hash_record_id": "<hash_record_id>",
    "blockchain_network": "polygon-mumbai",
    "anchor_status": "submitted",
    "transaction_hash": "0xdeadbeef..."
  }'
```

## 13. PROV introspection

```bash
curl http://localhost:8080/api/v1/bundles/<bundle_id>
curl http://localhost:8080/api/v1/bundles/<bundle_id>/graph
curl http://localhost:8080/api/v1/entities/<entity_id>
curl http://localhost:8080/api/v1/activities/<activity_id>
curl http://localhost:8080/api/v1/agents/<agent_id>
```

## 14. Integrity verification

```bash
curl http://localhost:8080/api/v1/audit/verify/<bundle_id>
```

The response lists every `hash_record` for the bundle's pipeline run, the
expected vs. recorded hash, and a `is_valid` overall verdict.

## 15. Errors (RFC 7807 Problem Details)

`Content-Type: application/problem+json`

```json
{
  "type": "about:blank",
  "title": "Invariant Violation",
  "status": 422,
  "detail": "wrapper_execution requires an existing source_artifact",
  "code": "InvariantViolationError",
  "correlation_id": "corr-001",
  "errors": {"input_artifact_id": "00000000-0000-0000-0000-000000000000"}
}
```

## 16. Reporting period (observability)

```bash
curl -X POST http://localhost:8080/api/v1/reporting-periods \
  -H "Content-Type: application/json" \
  -d '{
    "period_start": "2026-01-01T00:00:00+00:00",
    "period_end": "2026-02-01T00:00:00+00:00",
    "period_granularity": "monthly",
    "year": 2026,
    "month": 1,
    "period_label": "2026-01"
  }'

curl http://localhost:8080/api/v1/reporting-periods/<reporting_period_id>
```

## 17. Result aggregation links

```bash
curl -X POST http://localhost:8080/api/v1/result-aggregation-links \
  -H "Content-Type: application/json" \
  -d '{
    "parent_result_set_id": "<monthly_result_set_id>",
    "child_result_set_id": "<daily_result_set_id>",
    "aggregation_type": "daily_to_monthly",
    "parent_period_id": "<monthly_period_id>",
    "child_period_id": "<daily_period_id>"
  }'

curl http://localhost:8080/api/v1/calculation-result-sets/<annual_id>/aggregation-children
curl http://localhost:8080/api/v1/calculation-result-sets/<monthly_id>/aggregation-parents
```

## 18. Outbox events (observable stream)

```bash
curl "http://localhost:8080/api/v1/audit/outbox-events?limit=20&event_type=CALCULATION_APPROVED"
curl "http://localhost:8080/api/v1/audit/outbox-events?status=pending&aggregate_kind=calculation_result_set"
```

## 19. Pipeline trace and list

```bash
curl "http://localhost:8080/api/v1/pipeline-runs?limit=10&farm_reference=farm-acre-7"
curl http://localhost:8080/api/v1/pipeline-runs/<pipeline_run_id>/trace
curl http://localhost:8080/api/v1/pipeline-runs/<pipeline_run_id>/graph
```

## 20. Source artifact revision

```bash
curl -X POST http://localhost:8080/api/v1/source-artifact-revisions \
  -H "Content-Type: application/json" \
  -d '{
    "source_artifact_id": "<source_artifact_id>",
    "revision_number": 2,
    "storage_uri": "s3://agrotrace-raw/milk-2026-04-r2.xml",
    "content_hash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "is_current": true
  }'
```
