"""Templates SQL prontos para a seção Consultas de Proveniência."""

from __future__ import annotations

from typing import Any

DEFAULT_PLACEHOLDER_SQL = """SELECT
    outbox_event_id,
    event_type,
    aggregate_kind,
    status,
    created_at
FROM audit_outbox_event
WHERE pipeline_run_id = '{{pipeline_run_id}}'
ORDER BY created_at DESC
LIMIT 100"""


QUERY_TEMPLATES: list[dict[str, str]] = [
    {
        "id": "last_cycle_events",
        "title": "Últimos eventos do ciclo ativo",
        "description": "Eventos de outbox vinculados ao pipeline_run do ciclo.",
        "sql": """SELECT
    outbox_event_id,
    event_type,
    aggregate_kind,
    aggregate_id,
    status,
    pipeline_run_id,
    created_at,
    published_at
FROM audit_outbox_event
WHERE pipeline_run_id = '{{pipeline_run_id}}'
ORDER BY created_at DESC
LIMIT 100""",
    },
    {
        "id": "artifact_timeline",
        "title": "Linha do tempo de um arquivo",
        "description": "Artefato fonte e eventos relacionados no ciclo.",
        "sql": """SELECT
    sa.source_artifact_id,
    sa.original_filename,
    sa.content_hash,
    sa.received_at,
    oe.event_type,
    oe.status AS event_status,
    oe.created_at AS event_at
FROM pipeline_source_artifact sa
LEFT JOIN audit_outbox_event oe
    ON oe.pipeline_run_id = sa.pipeline_run_id
    AND oe.source_record_id = sa.source_artifact_id
WHERE sa.source_artifact_id = '{{source_artifact_id}}'
ORDER BY oe.created_at DESC
LIMIT 100""",
    },
    {
        "id": "farm_artifacts",
        "title": "Arquivos vinculados à fazenda ativa",
        "description": "Runs e artefatos da fazenda no período operacional.",
        "sql": """SELECT
    pr.pipeline_run_id,
    pr.run_code,
    pr.farm_reference,
    pr.reporting_period_reference,
    pr.run_status,
    sa.source_artifact_id,
    sa.original_filename,
    sa.content_hash
FROM pipeline_pipeline_run pr
JOIN pipeline_source_artifact sa ON sa.pipeline_run_id = pr.pipeline_run_id
WHERE pr.farm_reference = '{{farm_reference}}'
ORDER BY pr.started_at DESC
LIMIT 100""",
    },
    {
        "id": "calculations_from_run",
        "title": "Cálculos gerados no ciclo",
        "description": "Execuções e conjuntos de resultado do pipeline_run ativo.",
        "sql": """SELECT
    ce.calculation_execution_id,
    ce.execution_status,
    ce.started_at,
    ce.finished_at,
    crs.calculation_result_set_id,
    crs.result_set_status
FROM calculation_calculation_execution ce
JOIN calculation_calculation_result_set crs
    ON crs.calculation_execution_id = ce.calculation_execution_id
WHERE ce.pipeline_run_id = '{{pipeline_run_id}}'
ORDER BY ce.started_at DESC
LIMIT 100""",
    },
    {
        "id": "events_by_type",
        "title": "Eventos por tipo",
        "description": "Contagem de eventos de outbox agrupados por tipo no ciclo.",
        "sql": """SELECT
    event_type,
    status,
    COUNT(*) AS total
FROM audit_outbox_event
WHERE pipeline_run_id = '{{pipeline_run_id}}'
GROUP BY event_type, status
ORDER BY total DESC
LIMIT 100""",
    },
    {
        "id": "semantic_validations",
        "title": "Histórico de validações semânticas",
        "description": "Integração semântica e snapshots canônicos do ciclo.",
        "sql": """SELECT
    sie.semantic_integration_execution_id,
    sie.execution_status,
    sie.started_at,
    cs.canonical_snapshot_id,
    cs.snapshot_hash,
    cs.published_at AS snapshot_published_at
FROM semantic_semantic_integration_execution sie
LEFT JOIN semantic_canonical_snapshot cs
    ON cs.pipeline_run_id = sie.pipeline_run_id
WHERE sie.pipeline_run_id = '{{pipeline_run_id}}'
ORDER BY sie.started_at DESC
LIMIT 100""",
    },
    {
        "id": "pending_approval",
        "title": "Registros pendentes de aprovação",
        "description": "Reviews de cálculo sem decisão final no ciclo.",
        "sql": """SELECT
    cr.calculation_review_id,
    cr.calculation_result_set_id,
    cr.decision,
    cr.review_comment,
    cr.reviewed_at
FROM calculation_calculation_review cr
WHERE cr.pipeline_run_id = '{{pipeline_run_id}}'
  AND cr.decision = 'pending'
ORDER BY cr.reviewed_at DESC
LIMIT 100""",
    },
    {
        "id": "rejected_reviews",
        "title": "Registros rejeitados",
        "description": "Reviews com decisão rejeitada no ciclo.",
        "sql": """SELECT
    cr.calculation_review_id,
    cr.calculation_result_set_id,
    cr.decision,
    cr.review_comment,
    cr.reviewed_at
FROM calculation_calculation_review cr
WHERE cr.pipeline_run_id = '{{pipeline_run_id}}'
  AND cr.decision = 'rejected'
ORDER BY cr.reviewed_at DESC
LIMIT 100""",
    },
    {
        "id": "artifact_calc_hash",
        "title": "Relação entre arquivo, cálculo e hash",
        "description": "Artefato, resultado de cálculo e registros de hash.",
        "sql": """SELECT
    sa.source_artifact_id,
    sa.original_filename,
    sa.content_hash AS artifact_hash,
    crs.calculation_result_set_id,
    hr.hash_record_id,
    hr.subject_kind,
    hr.hash_algorithm,
    hr.hash_value
FROM pipeline_source_artifact sa
JOIN calculation_calculation_result_set crs
    ON crs.pipeline_run_id = sa.pipeline_run_id
LEFT JOIN audit_hash_record hr
    ON hr.pipeline_run_id = sa.pipeline_run_id
WHERE sa.pipeline_run_id = '{{pipeline_run_id}}'
ORDER BY sa.received_at
LIMIT 100""",
    },
    {
        "id": "published_data",
        "title": "Dados publicados",
        "description": "Execuções de publicação de resultado no ciclo.",
        "sql": """SELECT
    rpe.result_publication_execution_id,
    rpe.publication_status,
    rpe.published_at,
    rpe.calculation_result_set_id,
    rpe.pipeline_run_id
FROM calculation_result_publication_execution rpe
WHERE rpe.pipeline_run_id = '{{pipeline_run_id}}'
ORDER BY rpe.published_at DESC
LIMIT 100""",
    },
    {
        "id": "publication_evidence",
        "title": "Evidências geradas para publicação",
        "description": "Hashes de integridade registrados no ciclo.",
        "sql": """SELECT
    hr.hash_record_id,
    hr.subject_kind,
    hr.subject_id,
    hr.hash_algorithm,
    hr.hash_value,
    hr.computed_at
FROM audit_hash_record hr
WHERE hr.pipeline_run_id = '{{pipeline_run_id}}'
ORDER BY hr.computed_at DESC
LIMIT 100""",
    },
    {
        "id": "blockchain_anchors_for_run",
        "title": "Ancoragens espelhadas do pipeline_run",
        "description": "Espelho RF006 em audit_blockchain_anchor (somente provenance.db).",
        "sql": """SELECT
    ba.blockchain_anchor_id,
    ba.evidence_package_external_id,
    ba.package_hash,
    ba.merkle_root,
    ba.blockchain_network,
    ba.chain_id,
    ba.transaction_hash,
    ba.block_number,
    ba.anchor_status,
    ba.submitted_at,
    ba.confirmed_at,
    ba.anchor_provider,
    ba.anchor_mode
FROM audit_blockchain_anchor ba
WHERE ba.pipeline_run_id = '{{pipeline_run_id}}'
ORDER BY ba.submitted_at DESC
LIMIT 100""",
    },
    {
        "id": "full_farm_cycle",
        "title": "Ciclo completo da fazenda ativa",
        "description": "Resumo de runs, artefatos e eventos da fazenda.",
        "sql": """SELECT
    pr.pipeline_run_id,
    pr.run_code,
    pr.run_status,
    pr.reporting_period_reference,
    pr.started_at,
    (SELECT COUNT(*) FROM pipeline_source_artifact sa WHERE sa.pipeline_run_id = pr.pipeline_run_id) AS artifacts,
    (SELECT COUNT(*) FROM audit_outbox_event oe WHERE oe.pipeline_run_id = pr.pipeline_run_id) AS events
FROM pipeline_pipeline_run pr
WHERE pr.farm_reference = '{{farm_reference}}'
ORDER BY pr.started_at DESC
LIMIT 100""",
    },
]


def list_query_templates() -> list[dict[str, str]]:
    return list(QUERY_TEMPLATES)


def get_template_by_id(template_id: str) -> dict[str, str] | None:
    for t in QUERY_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None


def template_options() -> list[dict[str, str]]:
    return [{"label": t["title"], "value": t["id"]} for t in QUERY_TEMPLATES]
