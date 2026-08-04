"""Metadados de esquema do banco de proveniência para o explorador de auditoria."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import config
from services.provenance_sql_validator import ALLOWED_TABLE_PREFIXES

# Allowlist estática espelhando demo_tables.py do traceability-service
STATIC_TABLES: dict[str, tuple[str, ...]] = {
    "pipeline": (
        "pipeline_pipeline_run",
        "pipeline_source_artifact",
        "pipeline_source_artifact_revision",
        "pipeline_wrapper_definition",
        "pipeline_wrapper_execution",
        "pipeline_normalized_batch",
    ),
    "prov_core": (
        "prov_core_prov_bundle",
        "prov_core_prov_entity",
        "prov_core_prov_activity",
        "prov_core_prov_agent",
        "prov_core_prov_used",
        "prov_core_prov_generated",
        "prov_core_prov_derived_from",
        "prov_core_prov_associated_with",
        "prov_core_prov_revision",
        "prov_core_prov_attribute",
    ),
    "semantic": (
        "semantic_semantic_integration_execution",
        "semantic_canonical_snapshot",
        "semantic_canonical_snapshot_item",
        "semantic_ontology_resource_link",
    ),
    "calculation": (
        "calculation_calculation_method",
        "calculation_calculation_method_version",
        "calculation_calculation_parameter_set",
        "calculation_calculation_parameter_value",
        "calculation_calculation_execution",
        "calculation_calculation_result_set",
        "calculation_calculation_result_item",
        "calculation_calculation_review",
        "calculation_result_publication_execution",
    ),
    "audit": (
        "audit_hash_record",
        "audit_blockchain_anchor",
        "audit_outbox_event",
        "audit_audit_event",
    ),
    "reporting": (
        "reporting_period",
    ),
}


def _context_for_table(name: str) -> str:
    lower = name.lower()
    for ctx, tables in STATIC_TABLES.items():
        if lower in tables:
            return ctx
    for prefix, ctx in (
        ("pipeline_", "pipeline"),
        ("prov_core_", "prov_core"),
        ("semantic_", "semantic"),
        ("calculation_", "calculation"),
        ("audit_", "audit"),
        ("reporting_", "reporting"),
    ):
        if lower.startswith(prefix):
            return ctx
    return "other"


def _is_allowed_table(name: str) -> bool:
    return any(name.lower().startswith(p) for p in ALLOWED_TABLE_PREFIXES)


def _connect_ro(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def _table_info(conn: sqlite3.Connection, table: str) -> dict[str, Any]:
    cols: list[dict[str, Any]] = []
    pk_cols: list[str] = []
    for row in conn.execute(f"PRAGMA table_info({table})"):
        cid, name, col_type, notnull, default, pk = row
        col = {
            "name": name,
            "type": col_type or "TEXT",
            "nullable": not notnull,
            "primary_key": bool(pk),
        }
        cols.append(col)
        if pk:
            pk_cols.append(name)

    fks: list[dict[str, str]] = []
    try:
        for row in conn.execute(f"PRAGMA foreign_key_list({table})"):
            fks.append({
                "from_column": row[3],
                "to_table": row[2],
                "to_column": row[4],
            })
    except sqlite3.Error:
        pass

    return {
        "name": table,
        "columns": cols,
        "primary_keys": pk_cols,
        "foreign_keys": fks,
        "context": _context_for_table(table),
    }


def get_audit_schema(db_path: Path | None = None) -> dict[str, Any]:
    """Retorna metadados das tabelas consultáveis."""
    path = db_path or config.PROV_DB_PATH
    result: dict[str, Any] = {
        "source": "static",
        "db_path": str(path),
        "db_exists": path.exists(),
        "contexts": {},
        "tables": [],
        "allowed_table_names": [],
    }

    if not path.exists():
        tables_meta = [
            {"name": t, "columns": [], "primary_keys": [], "foreign_keys": [], "context": ctx}
            for ctx, names in STATIC_TABLES.items()
            for t in names
        ]
        result["tables"] = tables_meta
        result["allowed_table_names"] = [t["name"] for t in tables_meta]
        for t in tables_meta:
            result["contexts"].setdefault(t["context"], []).append(t["name"])
        return result

    try:
        with _connect_ro(path) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            allowed = [r[0] for r in rows if _is_allowed_table(r[0])]
            tables_meta = [_table_info(conn, t) for t in allowed]
            result["source"] = "live"
            result["tables"] = tables_meta
            result["allowed_table_names"] = allowed
            for t in tables_meta:
                result["contexts"].setdefault(t["context"], []).append(t["name"])
    except sqlite3.Error:
        tables_meta = [
            {"name": t, "columns": [], "primary_keys": [], "foreign_keys": [], "context": ctx}
            for ctx, names in STATIC_TABLES.items()
            for t in names
        ]
        result["tables"] = tables_meta
        result["allowed_table_names"] = [t["name"] for t in tables_meta]
        for t in tables_meta:
            result["contexts"].setdefault(t["context"], []).append(t["name"])

    return result


def allowed_table_set(db_path: Path | None = None) -> set[str]:
    schema = get_audit_schema(db_path)
    return {n.lower() for n in schema.get("allowed_table_names", [])}
