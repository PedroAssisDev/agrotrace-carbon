-- Auditoria: cada query deve retornar ZERO linhas quando o banco está correto
-- Executar: sqlite3 data/provenance.db < scripts/demo_repository_full_population/audit_queries.sql

-- 1) Entidades sem bundle
SELECT e.entity_id, e.pipeline_run_id
FROM prov_core_prov_entity e
LEFT JOIN prov_core_prov_bundle b ON b.bundle_id = e.bundle_id
WHERE b.bundle_id IS NULL;

-- 2) Atividades sem bundle
SELECT a.activity_id, a.pipeline_run_id
FROM prov_core_prov_activity a
LEFT JOIN prov_core_prov_bundle b ON b.bundle_id = a.bundle_id
WHERE b.bundle_id IS NULL;

-- 3) Relações used órfãs
SELECT u.used_id, u.activity_id, u.entity_id
FROM prov_core_prov_used u
LEFT JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
LEFT JOIN prov_core_prov_entity e ON e.entity_id = u.entity_id
WHERE a.activity_id IS NULL OR e.entity_id IS NULL;

-- 4) Relações generated órfãs
SELECT g.generated_id, g.activity_id, g.entity_id
FROM prov_core_prov_generated g
LEFT JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id
LEFT JOIN prov_core_prov_entity e ON e.entity_id = g.entity_id
WHERE a.activity_id IS NULL OR e.entity_id IS NULL;

-- 5) Relações derived_from órfãs
SELECT d.derived_id, d.generated_entity_id, d.source_entity_id
FROM prov_core_prov_derived_from d
LEFT JOIN prov_core_prov_entity ge ON ge.entity_id = d.generated_entity_id
LEFT JOIN prov_core_prov_entity se ON se.entity_id = d.source_entity_id
WHERE ge.entity_id IS NULL OR se.entity_id IS NULL;

-- 6) Relações associated_with órfãs
SELECT aw.association_id, aw.activity_id, aw.agent_id
FROM prov_core_prov_associated_with aw
LEFT JOIN prov_core_prov_activity a ON a.activity_id = aw.activity_id
LEFT JOIN prov_core_prov_agent ag ON ag.agent_id = aw.agent_id
WHERE a.activity_id IS NULL OR ag.agent_id IS NULL;

-- 7) Resultados sem cálculo
SELECT rs.calculation_result_set_id
FROM calculation_calculation_result_set rs
LEFT JOIN calculation_calculation_execution ce
  ON ce.calculation_execution_id = rs.calculation_execution_id
WHERE ce.calculation_execution_id IS NULL;

-- 8) Resultados publicados sem aprovação
SELECT pe.result_publication_execution_id, rs.result_set_status
FROM calculation_result_publication_execution pe
JOIN calculation_calculation_result_set rs
  ON rs.calculation_result_set_id = pe.calculation_result_set_id
WHERE rs.result_set_status NOT IN ('approved');

-- 9) Hashes sem subject (subject_id nulo — schema exige NOT NULL; checagem defensiva)
SELECT hash_record_id FROM audit_hash_record WHERE subject_id IS NULL;

-- 10) Blockchain anchors sem hash
SELECT ba.blockchain_anchor_id
FROM audit_blockchain_anchor ba
LEFT JOIN audit_hash_record hr ON hr.hash_record_id = ba.hash_record_id
WHERE hr.hash_record_id IS NULL;

-- 11) Aggregates sem atividade de agregação
SELECT e.entity_id, e.entity_kind
FROM prov_core_prov_entity e
WHERE e.entity_kind IN ('annual-aggregation', 'monthly-aggregation-january')
  AND e.entity_id NOT IN (
    SELECT g.entity_id FROM prov_core_prov_generated g
  );

-- 12) Annual aggregation Boa Vista sem 12 entradas
SELECT a.activity_id, COUNT(u.used_id) AS input_count
FROM prov_core_prov_activity a
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
LEFT JOIN prov_core_prov_used u ON u.activity_id = a.activity_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND a.name = 'annual_aggregation'
GROUP BY a.activity_id
HAVING input_count <> 12;

-- 13) Monthly aggregation janeiro Santa Clara sem 31 entradas
SELECT a.activity_id, COUNT(u.used_id) AS input_count
FROM prov_core_prov_activity a
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
LEFT JOIN prov_core_prov_used u ON u.activity_id = a.activity_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-m01-agg'
  AND a.name = 'monthly_aggregation_january'
GROUP BY a.activity_id
HAVING input_count <> 31;

-- 14) Registros críticos sem idempotency_key (quando coluna existe)
SELECT 'pipeline_run' AS tbl, pipeline_run_id AS id
FROM pipeline_pipeline_run
WHERE run_code LIKE 'demo_repo_%' AND idempotency_key IS NULL
UNION ALL
SELECT 'source_artifact', source_artifact_id
FROM pipeline_source_artifact sa
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = sa.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%' AND sa.idempotency_key IS NULL;

-- 15) Source artifacts demo sem hash
SELECT sa.source_artifact_id
FROM pipeline_source_artifact sa
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = sa.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%'
  AND sa.source_artifact_id NOT IN (
    SELECT subject_id FROM audit_hash_record WHERE subject_kind = 'source_artifact'
  );

-- 16) Normalized batches demo sem hash
SELECT nb.normalized_batch_id
FROM pipeline_normalized_batch nb
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = nb.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%'
  AND nb.normalized_batch_id NOT IN (
    SELECT subject_id FROM audit_hash_record WHERE subject_kind = 'normalized_batch'
  );

-- 17) Snapshots sem ontology_resource_link
SELECT cs.canonical_snapshot_id
FROM semantic_canonical_snapshot cs
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%'
  AND cs.canonical_snapshot_id NOT IN (
    SELECT canonical_snapshot_id FROM semantic_ontology_resource_link
    WHERE canonical_snapshot_id IS NOT NULL
  );
