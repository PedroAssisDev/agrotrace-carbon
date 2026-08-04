"""Linha do tempo de auditoria (não operacional)."""

from __future__ import annotations

from typing import Any

from services.cycle_state import status_label
from services.pipeline_display import AUDIT_STEP, DISPLAY_PIPELINE_STEPS, display_status_for_step, events_for_display_step
from services.provenance_event_catalog import canonical_event_type
from utils.hash_helpers import truncate_hash


def _artifact_for_step(cycle: dict, step_key: str) -> str:
    from pathlib import Path

    raw = cycle.get("raw_file") or {}
    original_name = raw.get("original_filename")
    if not original_name and raw.get("stored_path"):
        original_name = Path(str(raw["stored_path"])).name
    mapping = {
        "raw_upload": original_name,
        "original_file": original_name,
        "raw_hash": raw.get("sha256"),
        "wrapper": (cycle.get("wrapper") or {}).get("layout_id"),
        "normalized": f"{len(cycle.get('normalized_data') or [])} registro(s)",
        "canonical": (cycle.get("ontology") or {}).get("ontology_version"),
        "semantic": f"{(cycle.get('semantic_validation') or {}).get('total_validations', 0)} validações",
        "calculation": (cycle.get("calculation") or {}).get("co2e_total_kg"),
        "preliminary": "Resultado preliminar",
        "approval": (cycle.get("approval") or {}).get("decision"),
        "publication": (cycle.get("publication") or {}).get("ontology_version"),
        "evidence": (cycle.get("evidence_package") or {}).get("evidence_package_id"),
        "artifact_hashes": "Hashes finais",
        "merkle": (cycle.get("evidence_package") or {}).get("merkle_root"),
        "anchoring": (cycle.get("anchoring") or {}).get("transaction_id"),
        "verification": (cycle.get("integrity") or {}).get("final_status"),
        "prov_audit": "Cadeia completa",
    }
    val = mapping.get(step_key)
    return str(val) if val else "—"


def _hash_for_step(cycle: dict, step_key: str) -> str:
    raw = (cycle.get("raw_file") or {}).get("sha256")
    ont = (cycle.get("ontology") or {}).get("dataset_hash")
    pub = (cycle.get("publication") or {}).get("ontology_hash")
    merkle = (cycle.get("evidence_package") or {}).get("merkle_root")
    mapping = {
        "raw_hash": raw,
        "canonical": ont,
        "publication": pub,
        "merkle": merkle,
    }
    return truncate_hash(mapping.get(step_key) or "", 12)


def _mode_for_step(cycle: dict, orchestrator_step_id: str) -> str | None:
    step = (cycle.get("steps") or {}).get(orchestrator_step_id) or {}
    return step.get("mode") or step.get("source")


def _timeline_status(display_status: str, has_event: bool) -> str:
    if display_status in {"DONE", "DONE_WARNINGS", "APPROVED", "ANCHORED", "VERIFIED"}:
        return "Completo"
    if display_status == "RUNNING":
        return "Em execução"
    if display_status == "ERROR":
        return "Erro"
    if has_event:
        return "Com alerta"
    return "Pendente"


def build_audit_timeline(cycle: dict) -> list[dict[str, Any]]:
    """Constrói timeline de auditoria a partir das 18+1 etapas visuais."""
    all_steps = list(DISPLAY_PIPELINE_STEPS) + [AUDIT_STEP]
    rows = []
    for ds in all_steps:
        display_st = display_status_for_step(cycle, ds)
        step_events = events_for_display_step(cycle, ds)
        primary_event = step_events[0] if step_events else None
        event_type = primary_event.get("event_type") if primary_event else (
            ds.canonical_events[0] if ds.canonical_events else "—"
        )
        timestamp = primary_event.get("created_at") if primary_event else None
        if not timestamp:
            step_meta = (cycle.get("steps") or {}).get(ds.orchestrator_step_id) or {}
            timestamp = step_meta.get("finished_at") or step_meta.get("started_at")

        rows.append({
            "step_num": ds.step_num,
            "step_key": ds.step_key,
            "name": ds.label,
            "status": _timeline_status(display_st, bool(step_events)),
            "step_status": status_label(display_st),
            "event_type": event_type,
            "canonical_event": canonical_event_type(event_type) if event_type != "—" else "—",
            "service": ds.service,
            "phase": ds.phase,
            "timestamp": timestamp or "—",
            "artifact": _artifact_for_step(cycle, ds.step_key),
            "hash_short": _hash_for_step(cycle, ds.step_key),
            "mode": _mode_for_step(cycle, ds.orchestrator_step_id) or "—",
            "note": f"{len(step_events)} evento(s) registrado(s)" if step_events else "Sem evento registrado",
            "blockchain_zone": ds.blockchain_zone,
        })
    return rows
