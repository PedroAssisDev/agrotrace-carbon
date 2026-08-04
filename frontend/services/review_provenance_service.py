"""Proveniência dos eventos de revisão de cálculos."""

from __future__ import annotations

from typing import Any

from services import provenance_adapter
from services.provenance_event_catalog import emit_pipeline_event, REVIEW_EVENT_ALIASES

_REVIEW_EVENTS = {
    "CALCULATION_REVIEW_STARTED",
    "CALCULATION_ITEM_REVIEWED",
    "CALCULATION_INPUT_MAPPING_CHANGED",
    "CALCULATION_FACTOR_SELECTION_CHANGED",
    "CALCULATION_ITEM_APPROVED",
    "CALCULATION_ITEM_APPROVED_WITH_ZERO",
    "CALCULATION_ITEM_APPROVED_WITH_MANUAL_ADJUSTMENT",
    "CALCULATION_ITEM_REJECTED",
    "CALCULATION_ITEM_CORRECTION_REQUESTED",
    "ZERO_VALUE_ASSUMPTION_CONFIRMED",
    "FILE_CALCULATION_REVIEW_COMPLETED",
    "FILE_CALCULATION_APPROVED",
    "FILE_CALCULATION_REJECTED",
    "FINAL_APPROVAL_READY",
}


def _emit(cycle: dict, event_type: str, payload: dict) -> None:
    def _fn(c: dict, evt: str, pl: dict) -> None:
        result = provenance_adapter.register_provenance_event(evt, pl)
        events = c.setdefault("provenance_events", [])
        if isinstance(result, dict):
            events.append(result)
        else:
            events.append({"event_type": evt, **pl})

    emit_pipeline_event(cycle, event_type, payload, emit_fn=_fn)


def emit_review_started(cycle: dict, reviewer: str) -> None:
    _emit(cycle, "CALCULATION_REVIEW_STARTED", {
        "reviewer": reviewer,
        "file_review_id": (cycle.get("calculation_review") or {}).get("file_review_id"),
    })


def emit_calculation_item_reviewed(cycle: dict, item_id: str, decision: str, reviewer: str) -> None:
    _emit(cycle, "CALCULATION_ITEM_REVIEWED", {
        "calculation_item_id": item_id,
        "decision": decision,
        "reviewer": reviewer,
    })


def emit_input_mapping_changed(cycle: dict, item_id: str, swap: dict) -> None:
    _emit(cycle, "CALCULATION_INPUT_MAPPING_CHANGED", {
        "calculation_item_id": item_id,
        "swap": swap,
    })


def emit_factor_selection_changed(cycle: dict, item_id: str, changes: list[dict]) -> None:
    _emit(cycle, "CALCULATION_FACTOR_SELECTION_CHANGED", {
        "calculation_item_id": item_id,
        "changes": changes,
    })


def emit_calculation_item_approved(cycle: dict, item_id: str, reviewer: str, justification: str) -> None:
    _emit(cycle, "CALCULATION_ITEM_APPROVED", {
        "calculation_item_id": item_id,
        "reviewer": reviewer,
        "justification": justification,
    })


def emit_calculation_item_with_zero(cycle: dict, item_id: str, reviewer: str, justification: str) -> None:
    _emit(cycle, "CALCULATION_ITEM_APPROVED_WITH_ZERO", {
        "calculation_item_id": item_id,
        "reviewer": reviewer,
        "justification": justification,
    })


def emit_calculation_item_with_manual_adjustment(
    cycle: dict, item_id: str, reviewer: str, adjustment: dict,
) -> None:
    _emit(cycle, "CALCULATION_ITEM_APPROVED_WITH_MANUAL_ADJUSTMENT", {
        "calculation_item_id": item_id,
        "reviewer": reviewer,
        "adjustment": adjustment,
    })


def emit_calculation_item_rejected(cycle: dict, item_id: str, reviewer: str, justification: str) -> None:
    _emit(cycle, "CALCULATION_ITEM_REJECTED", {
        "calculation_item_id": item_id,
        "reviewer": reviewer,
        "justification": justification,
    })


def emit_calculation_item_correction_requested(
    cycle: dict, item_id: str, reviewer: str, justification: str,
) -> None:
    _emit(cycle, "CALCULATION_ITEM_CORRECTION_REQUESTED", {
        "calculation_item_id": item_id,
        "reviewer": reviewer,
        "justification": justification,
    })


def emit_zero_assumption_confirmed(cycle: dict, item_id: str, reviewer: str) -> None:
    _emit(cycle, "ZERO_VALUE_ASSUMPTION_CONFIRMED", {
        "calculation_item_id": item_id,
        "reviewer": reviewer,
    })


def emit_final_approval_ready(cycle: dict, reviewer: str) -> None:
    _emit(cycle, "FINAL_APPROVAL_READY", {"reviewer": reviewer})


def emit_file_calculation_approved(cycle: dict, reviewer: str, justification: str) -> None:
    _emit(cycle, "FILE_CALCULATION_APPROVED", {
        "reviewer": reviewer,
        "justification": justification,
    })
    _emit(cycle, "FILE_CALCULATION_REVIEW_COMPLETED", {
        "reviewer": reviewer,
        "status": "APPROVED",
    })


def emit_file_calculation_rejected(cycle: dict, reviewer: str, justification: str) -> None:
    _emit(cycle, "FILE_CALCULATION_REJECTED", {
        "reviewer": reviewer,
        "justification": justification,
    })


def list_review_events(cycle: dict) -> list[dict]:
    """Filtra eventos de revisão do ciclo."""
    events = cycle.get("provenance_events") or []
    names = set(_REVIEW_EVENTS)
    for aliases in REVIEW_EVENT_ALIASES.values():
        names.update(aliases)
    return [e for e in events if (e.get("event_type") or e.get("type")) in names]
