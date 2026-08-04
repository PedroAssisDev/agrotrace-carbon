-- Blockchain service SQLite schema (MVP)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS observer_state (
    state_key TEXT PRIMARY KEY,
    state_value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS anchor_request (
    anchor_request_id TEXT PRIMARY KEY,
    source_event_id TEXT NOT NULL UNIQUE,
    source_event_type TEXT NOT NULL,
    pipeline_run_id TEXT,
    calculation_result_set_id TEXT,
    reporting_period_id TEXT,
    request_scope TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS ix_anchor_request_status ON anchor_request(status);
CREATE INDEX IF NOT EXISTS ix_anchor_request_created_at ON anchor_request(created_at);

CREATE TABLE IF NOT EXISTS evidence_package (
    evidence_package_id TEXT PRIMARY KEY,
    anchor_request_id TEXT NOT NULL,
    package_type TEXT NOT NULL,
    package_version TEXT NOT NULL DEFAULT '1.0.0',
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    period_granularity TEXT NOT NULL,
    project_id_hash TEXT,
    farm_id_hash TEXT,
    management_unit_id_hash TEXT,
    canonical_payload_json TEXT,
    package_hash TEXT,
    merkle_root TEXT,
    metadata_hash TEXT,
    public_summary_enabled INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (anchor_request_id) REFERENCES anchor_request(anchor_request_id)
);

CREATE INDEX IF NOT EXISTS ix_evidence_package_anchor_request ON evidence_package(anchor_request_id);
CREATE INDEX IF NOT EXISTS ix_evidence_package_status ON evidence_package(status);

CREATE TABLE IF NOT EXISTS evidence_item (
    evidence_item_id TEXT PRIMARY KEY,
    evidence_package_id TEXT NOT NULL,
    item_order INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    source_table TEXT,
    source_record_id TEXT,
    source_event_id TEXT,
    source_hash_value TEXT,
    canonical_payload_json TEXT,
    item_hash TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (evidence_package_id) REFERENCES evidence_package(evidence_package_id)
);

CREATE INDEX IF NOT EXISTS ix_evidence_item_package_order ON evidence_item(evidence_package_id, item_order);

CREATE TABLE IF NOT EXISTS hash_record (
    hash_record_id TEXT PRIMARY KEY,
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    hash_algorithm TEXT NOT NULL,
    canonicalization_method TEXT NOT NULL,
    hash_value TEXT NOT NULL,
    payload_ref TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_hash_record_subject ON hash_record(subject_kind, subject_id);

CREATE TABLE IF NOT EXISTS blockchain_network (
    network_id TEXT PRIMARY KEY,
    network_code TEXT NOT NULL UNIQUE,
    network_name TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    chain_id TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS blockchain_transaction (
    blockchain_transaction_id TEXT PRIMARY KEY,
    evidence_package_id TEXT NOT NULL,
    network_id TEXT NOT NULL,
    anchoring_mode TEXT NOT NULL,
    anchoring_status TEXT NOT NULL,
    transaction_hash TEXT,
    block_number INTEGER,
    anchored_at TEXT,
    request_payload_json TEXT,
    response_payload_json TEXT,
    idempotency_key TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (evidence_package_id) REFERENCES evidence_package(evidence_package_id),
    FOREIGN KEY (network_id) REFERENCES blockchain_network(network_id)
);

CREATE INDEX IF NOT EXISTS ix_blockchain_transaction_package ON blockchain_transaction(evidence_package_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_blockchain_transaction_idempotency
    ON blockchain_transaction(idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS anchoring_attempt (
    anchoring_attempt_id TEXT PRIMARY KEY,
    anchor_request_id TEXT NOT NULL,
    evidence_package_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    status TEXT NOT NULL,
    error_code TEXT,
    error_message TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    FOREIGN KEY (anchor_request_id) REFERENCES anchor_request(anchor_request_id),
    FOREIGN KEY (evidence_package_id) REFERENCES evidence_package(evidence_package_id)
);

CREATE INDEX IF NOT EXISTS ix_anchoring_attempt_request ON anchoring_attempt(anchor_request_id);

CREATE TABLE IF NOT EXISTS verification_log (
    verification_log_id TEXT PRIMARY KEY,
    evidence_package_id TEXT NOT NULL,
    verification_type TEXT NOT NULL,
    expected_hash TEXT,
    computed_hash TEXT,
    is_valid INTEGER NOT NULL,
    verified_at TEXT NOT NULL,
    details_json TEXT,
    FOREIGN KEY (evidence_package_id) REFERENCES evidence_package(evidence_package_id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_log_id TEXT PRIMARY KEY,
    event_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    correlation_id TEXT,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    context_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_audit_log_entity ON audit_log(entity_type, entity_id);
