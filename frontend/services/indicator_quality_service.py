"""Indicadores de qualidade dos dados normalizados."""

from __future__ import annotations

from typing import Any

from services.indicator_extraction_service import num
from utils.formatting import NA as _NA


def data_quality_block(cycles: list[dict], period_series_fn) -> dict[str, Any]:
    raw_files = sum(1 for c in cycles if c.get("raw_file"))
    rows_read = rows_valid = rows_rejected = 0
    semantic_errors = semantic_warnings = inferences = 0
    incomplete_periods = 0
    errors_by_step: dict[str, int] = {}
    traceability_rows: list[dict] = []

    for c in cycles:
        w = c.get("wrapper") or {}
        rows_read += int(w.get("rows_read") or 0)
        rows_valid += int(w.get("rows_valid") or 0)
        rows_rejected += int(w.get("rows_rejected") or 0)
        sv = c.get("semantic_validation") or {}
        semantic_errors += int(sv.get("critical_errors") or 0)
        semantic_warnings += int(sv.get("warnings") or 0)
        inferences += int(sv.get("inferences") or 0)
        if w.get("rows_valid", 0) < w.get("rows_read", 0):
            incomplete_periods += 1
        for err in c.get("errors") or []:
            step = err.get("step") or "outro"
            errors_by_step[step] = errors_by_step.get(step, 0) + 1

        raw = c.get("raw_file") or {}
        traceability_rows.append({
            "cycle_id": c.get("cycle_id") or "—",
            "period": c.get("reporting_period") or "—",
            "file": raw.get("original_filename") or raw.get("stored_path") or "—",
            "hash": raw.get("sha256") or "—",
            "rows_valid": int(w.get("rows_valid") or 0),
            "rows_read": int(w.get("rows_read") or 0),
        })

    utilization = round(100.0 * rows_valid / rows_read, 1) if rows_read else None
    rejection_rate = round(100.0 * rows_rejected / rows_read, 1) if rows_read else None

    completeness_series = []
    for row in period_series_fn(cycles):
        c = next((x for x in cycles if x.get("cycle_id") == row.get("cycle_id")), {})
        w = c.get("wrapper") or {}
        rr, rv = int(w.get("rows_read") or 0), int(w.get("rows_valid") or 0)
        pct = round(100.0 * rv / rr, 1) if rr else None
        completeness_series.append({"period_label": row["period_label"], "pct": pct})

    return {
        "raw_files": raw_files,
        "normalized_records": rows_read,
        "valid_records": rows_valid,
        "alert_records": semantic_warnings,
        "error_records": semantic_errors + rows_rejected,
        "utilization_pct": utilization if utilization is not None else _NA,
        "rejection_pct": rejection_rate if rejection_rate is not None else _NA,
        "semantic_errors": semantic_errors,
        "semantic_warnings": semantic_warnings,
        "inferences": inferences,
        "missing_fields": _NA,
        "incomplete_periods": incomplete_periods,
        "errors_by_step": errors_by_step,
        "completeness_trend": completeness_series,
        "record_breakdown": {"válidos": rows_valid, "alertas": semantic_warnings, "erros": semantic_errors + rows_rejected},
        "traceability_rows": traceability_rows,
    }
