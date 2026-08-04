"""Execução segura de consultas SQL read-only sobre provenance.db."""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import threading
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import config
from services.provenance_schema_service import allowed_table_set
from services.provenance_sql_validator import DEFAULT_MAX_ROWS, validate_provenance_sql

logger = logging.getLogger("agrotrace.provenance_query")

QUERY_TIMEOUT_SEC = 5.0
DEFAULT_LIMIT = 100


def build_query_context_from_cycle(cycle: dict, ctx_farm_id: str | None = None) -> dict[str, str]:
    """Monta placeholders {{...}} a partir do ciclo ativo."""
    return {
        "pipeline_run_id": str(cycle.get("pipeline_run_id") or ""),
        "farm_reference": str(cycle.get("property_id") or ctx_farm_id or ""),
        "reporting_period": str(cycle.get("reporting_period") or ""),
        "reporting_period_id": str(cycle.get("reporting_period_id") or ""),
        "cycle_id": str(cycle.get("cycle_id") or ""),
        "source_artifact_id": str(cycle.get("source_artifact_id") or ""),
        "normalized_batch_id": str(cycle.get("normalized_batch_id") or ""),
        "canonical_snapshot_id": str(cycle.get("canonical_snapshot_id") or ""),
        "calculation_execution_id": str(cycle.get("calculation_execution_id") or ""),
        "calculation_result_set_id": str(cycle.get("calculation_result_set_id") or ""),
    }


def apply_context_placeholders(sql: str, context: dict[str, str] | None) -> str:
    if not context:
        return sql
    out = sql
    for key, value in context.items():
        out = out.replace(f"{{{{{key}}}}}", value)
    return out


def _serialize_value(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, (UUID, Decimal)):
        return str(val)
    if isinstance(val, bytes):
        return val.hex()
    return str(val)


def _connect_ro(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    conn.execute("PRAGMA busy_timeout = 3000")
    return conn


def _audit_log(
    sql: str,
    *,
    ok: bool,
    ms: float,
    row_count: int,
    tables: list[str] | None,
    context: dict | None,
    error: str | None = None,
) -> None:
    normalized = " ".join(sql.split()).lower()
    query_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    logger.info(
        "provenance_query audit hash=%s ok=%s ms=%.1f rows=%d tables=%s cycle=%s pipeline=%s error=%s",
        query_hash,
        ok,
        ms,
        row_count,
        tables,
        (context or {}).get("cycle_id"),
        (context or {}).get("pipeline_run_id"),
        error,
    )
    # TODO: confirmar — persistir metadados em audit_audit_event via ProvenanceRecorder
    # quando houver política de auditoria de consultas UI (sem gravar resultados).


def execute_provenance_query(
    sql: str,
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    context: dict[str, str] | None = None,
    db_path: Path | None = None,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> dict[str, Any]:
    """Executa consulta validada em modo read-only."""
    path = db_path or config.PROV_DB_PATH
    empty = {
        "columns": [],
        "rows": [],
        "row_count": 0,
        "execution_time_ms": 0,
        "truncated": False,
        "limit": limit,
        "offset": offset,
        "error": None,
        "ok": False,
    }

    if not path.exists():
        empty["error"] = "Banco de proveniência não encontrado. Execute a pipeline ou inicialize o bootstrap."
        _audit_log(sql, ok=False, ms=0, row_count=0, tables=None, context=context, error=empty["error"])
        return empty

    resolved_sql = apply_context_placeholders(sql, context)
    allowed = allowed_table_set(path)
    validation = validate_provenance_sql(
        resolved_sql,
        limit=limit,
        max_rows=max_rows,
        allowed_tables=allowed if allowed else None,
    )
    if not validation.ok:
        empty["error"] = validation.error
        _audit_log(resolved_sql, ok=False, ms=0, row_count=0, tables=validation.tables, context=context, error=validation.error)
        return empty

    exec_sql = validation.sql
    effective_limit = min(max(1, limit), max_rows)
    paginated_sql = exec_sql
    if offset > 0 and re_limit_missing_offset(exec_sql):
        paginated_sql = f"{exec_sql.rstrip().rstrip(';')}\nLIMIT {effective_limit} OFFSET {offset}"

    start = time.perf_counter()
    result_holder: dict[str, Any] = {}
    error_holder: list[str] = []

    def _run() -> None:
        try:
            with _connect_ro(path) as conn:
                cur = conn.execute(paginated_sql)
                rows_raw = cur.fetchmany(effective_limit + 1)
                columns = [d[0] for d in cur.description] if cur.description else []
                truncated = len(rows_raw) > effective_limit
                if truncated:
                    rows_raw = rows_raw[:effective_limit]
                rows = [
                    {col: _serialize_value(row[col]) for col in columns}
                    for row in rows_raw
                ]
                result_holder["columns"] = columns
                result_holder["rows"] = rows
                result_holder["row_count"] = len(rows)
                result_holder["truncated"] = truncated
        except sqlite3.Error as exc:
            error_holder.append(str(exc))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=QUERY_TIMEOUT_SEC)
    elapsed_ms = (time.perf_counter() - start) * 1000

    if thread.is_alive():
        empty["error"] = "Consulta interrompida por exceder o tempo máximo permitido."
        empty["execution_time_ms"] = round(elapsed_ms, 1)
        _audit_log(resolved_sql, ok=False, ms=elapsed_ms, row_count=0, tables=validation.tables, context=context, error=empty["error"])
        return empty

    if error_holder:
        empty["error"] = (
            "Erro SQL: verifique o nome das tabelas e colunas no explorador de esquema."
        )
        empty["execution_time_ms"] = round(elapsed_ms, 1)
        logger.debug("SQL error detail: %s", error_holder[0])
        _audit_log(resolved_sql, ok=False, ms=elapsed_ms, row_count=0, tables=validation.tables, context=context, error=error_holder[0])
        return empty

    _audit_log(
        resolved_sql,
        ok=True,
        ms=elapsed_ms,
        row_count=result_holder.get("row_count", 0),
        tables=validation.tables,
        context=context,
    )
    return {
        "columns": result_holder.get("columns", []),
        "rows": result_holder.get("rows", []),
        "row_count": result_holder.get("row_count", 0),
        "execution_time_ms": round(elapsed_ms, 1),
        "truncated": result_holder.get("truncated", False),
        "limit": effective_limit,
        "offset": offset,
        "error": None,
        "ok": True,
    }


def re_limit_missing_offset(sql: str) -> bool:
    """True se podemos aplicar OFFSET com LIMIT existente ou novo."""
    return True


def rows_to_csv(columns: list[str], rows: list[dict]) -> str:
    """Serializa resultado para CSV simples."""
    import csv
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in columns})
    return buf.getvalue()


def rows_to_tsv(columns: list[str], rows: list[dict]) -> str:
    lines = ["\t".join(columns)]
    for row in rows:
        lines.append("\t".join(str(row.get(c, "")) for c in columns))
    return "\n".join(lines)
