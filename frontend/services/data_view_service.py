"""View layer — dados brutos, wrapper, normalizado e qualidade."""

from __future__ import annotations

from typing import Any


def build_raw_data_view(cycle: dict) -> dict[str, Any]:
    raw = cycle.get("raw_file") or {}
    return {
        "filename": raw.get("original_filename"),
        "property_id": cycle.get("property_id"),
        "period": cycle.get("reporting_period"),
        "layout": raw.get("layout_id"),
        "size_bytes": raw.get("size_bytes"),
        "extension": raw.get("extension"),
        "uploaded_at": raw.get("stored_at"),
        "sha256": raw.get("sha256"),
        "stored_path": raw.get("stored_path"),
    }


def build_wrapper_view(cycle: dict) -> dict[str, Any]:
    w = cycle.get("wrapper") or {}
    return {
        "layout_id": w.get("layout_id"),
        "wrapper_version": w.get("wrapper_version", "—"),
        "rows_read": w.get("rows_read", 0),
        "rows_valid": w.get("rows_valid", 0),
        "rows_rejected": w.get("rows_rejected", 0),
        "errors": w.get("errors") or [],
        "warnings": w.get("warnings") or [],
        "status": (cycle.get("steps") or {}).get("wrapper", {}).get("status", "PENDING"),
        "mode": w.get("mode") or w.get("source"),
    }


def build_normalized_table_rows(cycle: dict) -> list[dict]:
    rows = cycle.get("normalized_data") or []
    out = []
    for r in rows[:200]:
        if not isinstance(r, dict):
            continue
        out.append({
            "variavel": r.get("variable") or r.get("field") or "—",
            "valor": r.get("value"),
            "unidade": r.get("unit", "—"),
            "periodo": r.get("period_start") or cycle.get("reporting_period", "—"),
            "fonte": r.get("source", "wrapper"),
            "status": r.get("status", "—"),
            "observacao": r.get("note") or r.get("validation_message", ""),
        })
    return out


def build_data_quality_view(cycle: dict) -> dict[str, Any]:
    w = cycle.get("wrapper") or {}
    read = max(int(w.get("rows_read") or 0), 1)
    valid = int(w.get("rows_valid") or 0)
    rejected = int(w.get("rows_rejected") or 0)
    sem = cycle.get("semantic_validation") or {}
    return {
        "valid_rate_pct": round(100 * valid / read, 1) if read else 0,
        "rejection_rate_pct": round(100 * rejected / read, 1) if read else 0,
        "missing_fields": sem.get("missing_fields") or [],
        "warnings": (w.get("warnings") or []) + (sem.get("warnings_list") or []),
        "errors": (w.get("errors") or []) + (sem.get("errors_list") or []),
        "used_in_calculation": valid,
        "discarded": rejected,
        "critical_errors": sem.get("critical_errors", 0),
    }
