"""Resolução de eventos de proveniência por ciclo (sem fallback silencioso)."""

from __future__ import annotations

from typing import Any

from services.provenance_view_service import enrich_events, filter_enriched_events


def _match_event_to_cycle(event: dict, cycle_id: str, cycle: dict) -> bool:
    payload = event.get("payload_json") or event.get("payload") or {}
    if str(event.get("aggregate_id")) == str(cycle_id):
        return True
    if payload.get("cycle_id") == cycle_id:
        return True
    pipeline_run = cycle.get("pipeline_run_id")
    if pipeline_run and str(event.get("pipeline_execution_id")) == str(pipeline_run):
        return True
    return False


def filter_events_for_cycle(
    events: list[dict],
    cycle_id: str,
    cycle: dict,
) -> list[dict]:
    """Filtra eventos estritamente vinculados ao ciclo (sem fallback global)."""
    if not cycle_id or not events:
        return []
    return [e for e in events if _match_event_to_cycle(e, cycle_id, cycle)]


def resolve_cycle_events(
    all_events: list[dict],
    cycle: dict,
    *,
    include_global_fallback: bool = False,
) -> dict[str, Any]:
    """Separa eventos do ciclo dos globais.

    Returns:
        cycle_events: eventos enriquecidos do ciclo
        global_events: eventos globais (quando solicitado e sem match)
        has_cycle_match: True se houve match específico
        used_global_fallback: True se caiu em globais por falta de match
    """
    cycle_id = cycle.get("cycle_id") or ""
    matched = filter_events_for_cycle(all_events, cycle_id, cycle)
    has_match = bool(matched)

    if not has_match:
        cycle_prov = cycle.get("provenance_events") or []
        if cycle_prov:
            matched = list(cycle_prov)
            has_match = bool(matched)

    enriched_cycle = enrich_events(matched) if matched else []

    global_events: list[dict] = []
    used_fallback = False
    if not has_match and include_global_fallback and all_events:
        global_events = enrich_events(all_events)
        used_fallback = True

    return {
        "cycle_events": enriched_cycle,
        "global_events": global_events,
        "has_cycle_match": has_match,
        "used_global_fallback": used_fallback,
    }


def most_recent_event(events: list[dict]) -> dict | None:
    """Retorna evento com maior timestamp (created_at)."""
    if not events:
        return None
    return max(events, key=lambda e: e.get("created_at") or "")


def filter_events_for_ui(
    events: list[dict],
    *,
    phase: str | None = None,
    service: str | None = None,
    status: str | None = None,
    event_type: str | None = None,
    search: str | None = None,
) -> list[dict]:
    """Aplica filtros locais de proveniência (reusa filter_enriched_events)."""
    filtered = filter_enriched_events(events, phase=phase, service=service, status=status)
    if event_type and event_type != "all":
        filtered = [
            e for e in filtered
            if e.get("event_type") == event_type or e.get("canonical_event_type") == event_type
        ]
    if search:
        q = search.lower().strip()
        filtered = [
            e for e in filtered
            if q in (e.get("event_type") or "").lower()
            or q in (e.get("service") or "").lower()
            or q in str(e.get("payload_json") or e.get("payload") or "").lower()
        ]
    return filtered


def unique_filter_options(events: list[dict]) -> dict[str, list[dict]]:
    """Opções para dropdowns de filtros locais."""
    phases = sorted({e.get("phase") for e in events if e.get("phase")})
    services = sorted({e.get("service") for e in events if e.get("service") and e.get("service") != "—"})
    statuses = sorted({e.get("status") or "ok" for e in events})
    event_types = sorted({e.get("event_type") for e in events if e.get("event_type")})

    def _opts(values: list, all_label: str = "Todos") -> list[dict]:
        return [{"label": all_label, "value": "all"}] + [{"label": v, "value": v} for v in values]

    return {
        "phases": _opts(phases, "Todas as fases"),
        "services": _opts(services, "Todos os serviços"),
        "statuses": _opts(statuses, "Todos os status"),
        "event_types": _opts(event_types, "Todos os tipos"),
    }
