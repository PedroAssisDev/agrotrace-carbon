"""View layer — dados brutos, wrapper, normalizado e qualidade."""

from __future__ import annotations

from typing import Any

from config import LAYOUT_OPTIONS
from services.cycle_status_service import resolve_managerial_status
from services.provenance_adapter import build_event_table_rows
from services.provenance_view_service import enrich_events
from utils.global_filter import format_cycle_period_label
from utils.hash_helpers import truncate_hash

_LAYOUT_LABELS = {
    "intraday:v1": "Intradiário",
    "monthly:v1": "Produção mensal",
    "annual:v1": "Anual",
    "intraday": "Intradiário",
    "monthly": "Produção mensal",
    "annual": "Anual",
}

# Eventos operacionais relevantes para a aba resumo da Entrada de Dados (sem blockchain).
_ENTRY_EVENT_TYPES = {
    "RAW_DATA_RECEIVED", "RAW_DATA_UPLOADED", "RAW_DATA_REGISTERED",
    "ORIGINAL_FILE_STORED", "RAW_FILE_HASH_CREATED",
    "WRAPPER_EXECUTION_STARTED", "WRAPPER_EXECUTED",
    "NORMALIZED_BATCH_CREATED", "NORMALIZED_DATA_DERIVED_FROM_RAW_DATA",
    "CANONICAL_MODEL_POPULATION_STARTED", "CANONICAL_MODEL_POPULATED", "CANONICAL_PUBLISHED",
    "SEMANTIC_VALIDATION_STARTED", "SEMANTIC_VALIDATION_COMPLETED", "SEMANTIC_MAPPING_COMPLETED",
    "CALCULATION_EXECUTION_STARTED", "CALCULATION_EXECUTED",
    "PRELIMINARY_RESULT_CREATED", "CALCULATION_PRELIMINARY_RESULT_CREATED",
    "HUMAN_APPROVAL_REQUESTED",
}


def build_raw_data_view(cycle: dict) -> dict[str, Any]:
    raw = cycle.get("raw_file") or {}
    return {
        "filename": raw.get("original_filename"),
        "property_id": cycle.get("property_id") or raw.get("property_id"),
        "period": cycle.get("reporting_period") or raw.get("reporting_period"),
        "layout": raw.get("layout_id") or cycle.get("layout_id"),
        "size_bytes": raw.get("file_size_bytes") if raw.get("file_size_bytes") is not None else raw.get("size_bytes"),
        "extension": raw.get("file_extension") or raw.get("extension"),
        "uploaded_at": raw.get("uploaded_at") or raw.get("stored_at"),
        "sha256": raw.get("sha256"),
        "artifact_id": raw.get("artifact_id"),
        # Path absoluto não deve ir para a UI; mantido só para consumidores internos.
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


def _layout_label(cycle: dict) -> str:
    layout_id = cycle.get("layout_id") or (cycle.get("wrapper") or {}).get("layout_id") or ""
    if layout_id in _LAYOUT_LABELS:
        return _LAYOUT_LABELS[layout_id]
    for key, val in LAYOUT_OPTIONS.items():
        if val == layout_id or key == layout_id:
            return _LAYOUT_LABELS.get(val, _LAYOUT_LABELS.get(key, layout_id or "—"))
    return layout_id or "—"


def _cycle_has_error(cycle: dict) -> bool:
    if cycle.get("errors"):
        return True
    for step in (cycle.get("steps") or {}).values():
        if step.get("status") == "ERROR":
            return True
    return False


def _cycle_has_warnings(cycle: dict) -> bool:
    for step in (cycle.get("steps") or {}).values():
        if step.get("status") == "DONE_WARNINGS":
            return True
    if cycle.get("wrapper"):
        quality = build_data_quality_view(cycle)
        if quality.get("warnings") or quality.get("critical_errors", 0) > 0:
            return True
    return False


def _cycle_processed_ok(cycle: dict) -> bool:
    calc_step = (cycle.get("steps") or {}).get("calculation", {}).get("status")
    has_calc = bool(cycle.get("calculation")) or calc_step in {"DONE", "DONE_WARNINGS"}
    return has_calc and not _cycle_has_error(cycle)


def build_data_entry_overview(cycles: list[dict]) -> dict[str, int]:
    """Contagens read-only para cards resumidos da Entrada de Dados."""
    total = len(cycles)
    processed = sum(1 for c in cycles if _cycle_processed_ok(c))
    with_alert = sum(1 for c in cycles if _cycle_has_warnings(c) and not _cycle_has_error(c))
    with_error = sum(1 for c in cycles if _cycle_has_error(c))
    pending = sum(1 for c in cycles if resolve_managerial_status(c).key == "pending_approval")
    return {
        "total": total,
        "processed": processed,
        "with_alert": with_alert,
        "with_error": with_error,
        "pending_approval": pending,
    }


def build_data_entry_rows(cycles: list[dict]) -> list[dict]:
    """Linhas da tabela principal da Entrada de Dados."""
    rows = []
    for c in cycles:
        raw = build_raw_data_view(c) if c.get("raw_file") else {}
        st = resolve_managerial_status(c)
        sha = raw.get("sha256") or ""
        rows.append({
            "cycle_id": c.get("cycle_id"),
            "arquivo": raw.get("filename") or c.get("cycle_id", "—"),
            "fazenda": c.get("property_name", "—"),
            "periodo": format_cycle_period_label(c),
            "layout": _layout_label(c),
            "data_envio": raw.get("uploaded_at") or c.get("created_at", "—"),
            "hash_resumido": truncate_hash(str(sha), 6) if sha else "—",
            "status": st.label,
            "status_variant": st.variant,
            "proxima_acao": st.next_action or "—",
            "next_href": st.next_href,
        })
    return rows


def build_file_events_view(cycle: dict, *, limit: int = 20) -> list[dict]:
    """Resumo de eventos operacionais do ciclo/arquivo (sem auditoria blockchain)."""
    events = cycle.get("provenance_events") or []
    enriched = enrich_events(events)
    operational = [
        e for e in enriched
        if e.get("phase") != "blockchain"
        and (
            e.get("event_type") in _ENTRY_EVENT_TYPES
            or e.get("canonical_event_type") in _ENTRY_EVENT_TYPES
        )
    ]
    if not operational:
        operational = [e for e in enriched if e.get("phase") != "blockchain"]
    operational = operational[:limit]
    return build_event_table_rows(operational)


def _cycle_upload_timestamp(cycle: dict) -> str:
    raw = cycle.get("raw_file") or {}
    return (
        raw.get("uploaded_at")
        or cycle.get("updated_at")
        or cycle.get("created_at")
        or ""
    )


def pick_latest_cycle(cycles: list[dict]) -> dict:
    """Retorna o ciclo/arquivo mais recentemente carregado."""
    if not cycles:
        return {}
    return max(cycles, key=_cycle_upload_timestamp)


def build_farm_upload_cycles(all_cycles: list[dict], farm_id: str | None) -> list[dict]:
    """Todos os arquivos/ciclos carregados para a fazenda (inclui erros; sem filtro analítico)."""
    from utils.global_filter import cycles_for_farm

    if not farm_id:
        return []
    return sorted(cycles_for_farm(all_cycles, farm_id), key=_cycle_upload_timestamp, reverse=True)


def build_file_select_options(cycles: list[dict]) -> list[dict]:
    """Opções do seletor de arquivo no painel de detalhes."""
    ordered = sorted(cycles, key=_cycle_upload_timestamp, reverse=True)
    options: list[dict] = []
    for c in ordered:
        cid = c.get("cycle_id")
        if not cid:
            continue
        raw = build_raw_data_view(c) if c.get("raw_file") else {}
        name = raw.get("filename") or c.get("cycle_id", "Arquivo")
        period = c.get("reporting_period") or raw.get("period") or "—"
        label = f"{name} — {period}"
        if _cycle_has_error(c):
            label = f"{name} — {period} · Erro"
        elif _cycle_has_warnings(c):
            label = f"{name} — {period} · Alerta"
        options.append({
            "label": label,
            "value": cid,
        })
    return options


def resolve_detail_cycle(
    cycles: list[dict],
    active_cycle: dict | None,
    context_cycle_id: str | None = None,
) -> tuple[dict, str | None]:
    """Resolve ciclo exibido no painel; padrão = último carregado."""
    if not cycles:
        return {}, None
    cycle_ids = {c.get("cycle_id") for c in cycles if c.get("cycle_id")}
    latest = pick_latest_cycle(cycles)
    preferred_id = context_cycle_id or (active_cycle or {}).get("cycle_id")
    if preferred_id in cycle_ids:
        selected = next(c for c in cycles if c.get("cycle_id") == preferred_id)
        return selected, preferred_id
    latest_id = latest.get("cycle_id")
    return latest, latest_id
