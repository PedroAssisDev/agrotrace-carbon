-- Linhagem e apresentação da demonstração demo_repository_full_population
-- Executar: sqlite3 data/provenance.db < scripts/demo_repository_full_population/lineage_queries.sql

-- 1) Todos os pipeline_runs de demonstração
SELECT pipeline_run_id, run_code, farm_reference, reporting_period_reference, run_status, started_at
FROM pipeline_pipeline_run
WHERE run_code LIKE 'demo_repo_%'
ORDER BY started_at;

-- 2) Bundles por pipeline_run
SELECT b.bundle_id, b.pipeline_run_id, r.run_code, b.bundle_type, b.status, b.created_at
FROM prov_core_prov_bundle b
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = b.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%'
ORDER BY r.run_code, b.bundle_type;

-- 3) Entidades por bundle
SELECT e.entity_id, e.bundle_id, e.entity_type, e.entity_kind, e.name, e.content_hash
FROM prov_core_prov_entity e
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = e.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%'
ORDER BY r.run_code, e.entity_type;

-- 4) Atividades por bundle
SELECT a.activity_id, a.bundle_id, a.activity_type, a.name, a.status, a.recorded_at
FROM prov_core_prov_activity a
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%'
ORDER BY r.run_code, a.activity_type;

-- 5) Relações PROV (used, generated, derived_from)
SELECT 'used' AS rel, u.used_id, u.activity_id, u.entity_id, u.role
FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%'
UNION ALL
SELECT 'generated', g.generated_id, g.activity_id, g.entity_id, NULL
FROM prov_core_prov_generated g
JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%'
UNION ALL
SELECT 'derived_from', d.derived_id, d.generated_entity_id, d.source_entity_id, d.derivation_type
FROM prov_core_prov_derived_from d
JOIN prov_core_prov_entity e ON e.entity_id = d.generated_entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = e.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%';

-- 6) Linhagem caso anual direto (Fazenda São Pedro)
SELECT r.run_code, sa.original_filename, nb.batch_code, cs.snapshot_label, rs.result_set_status
FROM pipeline_pipeline_run r
LEFT JOIN pipeline_source_artifact sa ON sa.pipeline_run_id = r.pipeline_run_id
LEFT JOIN pipeline_normalized_batch nb ON nb.pipeline_run_id = r.pipeline_run_id
LEFT JOIN semantic_canonical_snapshot cs ON cs.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_calculation_result_set rs ON rs.pipeline_run_id = r.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026';

-- 7) Linhagem caso mensal → anual (Boa Vista)
SELECT r.run_code, r.reporting_period_reference, cs.snapshot_label
FROM pipeline_pipeline_run r
LEFT JOIN semantic_canonical_snapshot cs ON cs.pipeline_run_id = r.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista'
ORDER BY r.reporting_period_reference;

-- 8) Linhagem caso diário → mensal → anual (Santa Clara)
SELECT r.run_code, r.reporting_period_reference
FROM pipeline_pipeline_run r
WHERE r.farm_reference = 'Fazenda Santa Clara'
ORDER BY r.reporting_period_reference;

-- 9) Os 12 meses da Fazenda Boa Vista
SELECT run_code, reporting_period_reference
FROM pipeline_pipeline_run
WHERE farm_reference = 'Fazenda Boa Vista'
  AND reporting_period_reference LIKE '2026-%'
  AND reporting_period_reference NOT LIKE '%-annual%'
ORDER BY reporting_period_reference;

-- 10) Os 31 dias de janeiro da Fazenda Santa Clara
SELECT run_code, reporting_period_reference
FROM pipeline_pipeline_run
WHERE farm_reference = 'Fazenda Santa Clara'
  AND reporting_period_reference LIKE '2026-01-%'
ORDER BY reporting_period_reference;

-- 11) Revisões do caso de reprocessamento
SELECT sar.source_artifact_revision_id, sar.revision_number, sar.is_current, sar.content_hash
FROM pipeline_source_artifact_revision sar
JOIN pipeline_source_artifact sa ON sa.source_artifact_id = sar.source_artifact_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = sa.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_reprocessing_%';

SELECT pr.prov_revision_id, pr.previous_entity_id, pr.new_entity_id, pr.revision_reason
FROM prov_core_prov_revision pr;

-- 12) Resultados preliminares
SELECT rs.calculation_result_set_id, r.run_code, rs.result_set_status, rs.generated_at
FROM calculation_calculation_result_set rs
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%'
  AND rs.result_set_status = 'preliminary';

-- 13) Aprovações humanas
SELECT cr.calculation_review_id, r.run_code, cr.decision, cr.review_comment, cr.reviewed_at
FROM calculation_calculation_review cr
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cr.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%'
  AND cr.decision = 'approved';

-- 14) Publicações finais
SELECT pe.result_publication_execution_id, r.run_code, pe.publication_status, pe.published_at
FROM calculation_result_publication_execution pe
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = pe.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%';

-- 15) Hashes
SELECT hr.hash_record_id, r.run_code, hr.subject_kind, hr.subject_id, hr.hash_value
FROM audit_hash_record hr
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = hr.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%';

-- 16) Ancoragens blockchain simuladas
SELECT ba.blockchain_anchor_id, ba.blockchain_network, ba.transaction_hash, ba.anchor_status, ba.anchored_at
FROM audit_blockchain_anchor ba
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ba.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_%';

-- 17) Eventos de auditoria
SELECT ae.audit_event_id, ae.event_type, ae.subject_kind, ae.subject_id, ae.recorded_at
FROM audit_audit_event ae
ORDER BY ae.recorded_at;

-- 18) Eventos de outbox
SELECT oe.outbox_event_id, oe.aggregate_kind, oe.event_type, oe.status, oe.created_at
FROM audit_outbox_event oe
ORDER BY oe.created_at DESC
LIMIT 50;
