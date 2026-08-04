"""View layer — proveniência e timeline canônica."""

from __future__ import annotations

from services.pipeline_display import AUDIT_STEP, DISPLAY_PIPELINE_STEPS
from services.provenance_event_catalog import canonical_event_type

CANONICAL_EVENT_ORDER: list[str] = []
for ds in DISPLAY_PIPELINE_STEPS:
    CANONICAL_EVENT_ORDER.extend(ds.canonical_events)
CANONICAL_EVENT_ORDER.extend(AUDIT_STEP.canonical_events)

_EVENT_META: dict[str, dict] = {}
for ds in DISPLAY_PIPELINE_STEPS:
    for ev in ds.canonical_events:
        _EVENT_META[ev] = {"phase": ds.phase, "service": ds.service, "step_label": ds.label}
for ev in AUDIT_STEP.canonical_events:
    _EVENT_META[ev] = {"phase": AUDIT_STEP.phase, "service": AUDIT_STEP.service, "step_label": AUDIT_STEP.label}


def enrich_events(events: list[dict]) -> list[dict]:
    out = []
    for e in events:
        et = e.get("event_type", "")
        canonical = canonical_event_type(et)
        meta = _EVENT_META.get(canonical, _EVENT_META.get(et, {"phase": "operational", "service": "—", "step_label": "—"}))
        order = CANONICAL_EVENT_ORDER.index(canonical) if canonical in CANONICAL_EVENT_ORDER else (
            CANONICAL_EVENT_ORDER.index(et) if et in CANONICAL_EVENT_ORDER else 999
        )
        out.append({**e, "canonical_event_type": canonical, **meta, "canonical_order": order})
    return sorted(out, key=lambda x: (x.get("canonical_order", 999), x.get("created_at", "")))


def filter_enriched_events(
    events: list[dict],
    phase: str | None = None,
    service: str | None = None,
    status: str | None = None,
) -> list[dict]:
    enriched = enrich_events(events)
    if phase and phase != "all":
        enriched = [e for e in enriched if e.get("phase") == phase]
    if service and service != "all":
        enriched = [e for e in enriched if service.lower() in (e.get("service") or "").lower()]
    if status and status != "all":
        enriched = [e for e in enriched if (e.get("status") or "ok") == status]
    return enriched


def build_derivation_graph(events: list[dict]) -> list[dict]:
    """Grafo simples: evento → próximo na cadeia canônica presente."""
    present = {canonical_event_type(e.get("event_type", "")) for e in events}
    present.update(e.get("event_type") for e in events)
    edges = []
    for i, et in enumerate(CANONICAL_EVENT_ORDER):
        if et not in present:
            continue
        if i + 1 < len(CANONICAL_EVENT_ORDER):
            nxt = CANONICAL_EVENT_ORDER[i + 1]
            if nxt in present:
                edges.append({"from": et, "to": nxt})
    return edges
