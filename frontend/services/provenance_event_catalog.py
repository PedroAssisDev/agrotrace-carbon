"""Catálogo de eventos canônicos e aliases legados do pipeline."""

from __future__ import annotations

from typing import Any

# Canônico → aliases legados (compatibilidade com telas e stepper de 18 etapas)
EVENT_ALIASES: dict[str, list[str]] = {
    "RAW_DATA_RECEIVED": ["RAW_DATA_UPLOADED"],
    "RAW_DATA_UPLOADED": ["RAW_DATA_RECEIVED"],
    "CANONICAL_MODEL_POPULATED": ["CANONICAL_PUBLISHED", "SEMANTIC_MAPPING_COMPLETED"],
    "PRELIMINARY_RESULT_CREATED": ["CALCULATION_PRELIMINARY_RESULT_CREATED"],
    "MERKLE_ROOT_CREATED": ["LOCAL_HASH_CREATED"],
    "INTEGRITY_VERIFICATION_EXECUTED": ["VERIFICATION_EXECUTED"],
    # Revisão e aprovação por cálculo
    "CALCULATION_REVIEW_STARTED": ["REVIEW_STARTED"],
    "CALCULATION_ITEM_REVIEWED": ["ITEM_REVIEWED"],
    "CALCULATION_INPUT_MAPPING_CHANGED": ["INPUT_MAPPING_CHANGED"],
    "CALCULATION_FACTOR_SELECTION_CHANGED": ["FACTOR_SELECTION_CHANGED"],
    "CALCULATION_ITEM_APPROVED": ["ITEM_APPROVED"],
    "CALCULATION_ITEM_APPROVED_WITH_ZERO": ["ITEM_APPROVED_WITH_ZERO"],
    "CALCULATION_ITEM_APPROVED_WITH_MANUAL_ADJUSTMENT": ["ITEM_APPROVED_WITH_MANUAL_ADJ"],
    "CALCULATION_ITEM_REJECTED": ["ITEM_REJECTED"],
    "CALCULATION_ITEM_CORRECTION_REQUESTED": ["ITEM_CORRECTION_REQUESTED"],
    "ZERO_VALUE_ASSUMPTION_CONFIRMED": ["ZERO_ASSUMPTION_CONFIRMED"],
    "FILE_CALCULATION_REVIEW_COMPLETED": ["FILE_REVIEW_COMPLETED"],
    "FILE_CALCULATION_APPROVED": ["FILE_APPROVED"],
    "FILE_CALCULATION_REJECTED": ["FILE_REJECTED"],
    "FINAL_APPROVAL_READY": ["APPROVAL_READY"],
}

# Alias reverso para serviços de revisão
REVIEW_EVENT_ALIASES: dict[str, list[str]] = {
    k: v for k, v in EVENT_ALIASES.items()
    if k.startswith("CALCULATION_") or k.startswith("FILE_") or k.startswith("ZERO_") or k == "FINAL_APPROVAL_READY"
}

# Inverso: legado → canônico preferido
_LEGACY_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in EVENT_ALIASES.items():
    for alias in aliases:
        _LEGACY_TO_CANONICAL[alias] = canonical


def canonical_event_type(event_type: str) -> str:
    """Normaliza evento legado para o nome canônico preferido."""
    return _LEGACY_TO_CANONICAL.get(event_type, event_type)


def all_event_names(event_type: str) -> list[str]:
    """Retorna o tipo canônico e aliases legados associados."""
    canonical = canonical_event_type(event_type)
    names = [canonical]
    for alias in EVENT_ALIASES.get(canonical, []):
        if alias not in names:
            names.append(alias)
    if event_type not in names:
        names.append(event_type)
    return names


def emit_pipeline_event(
    cycle: dict,
    event_type: str,
    payload: dict,
    *,
    emit_fn,
    include_legacy: bool = True,
) -> None:
    """Emite evento canônico e aliases legados via função emit do orquestrador."""
    payload = dict(payload)
    payload.setdefault("cycle_id", cycle.get("cycle_id"))
    if cycle.get("pipeline_run_id"):
        payload.setdefault("pipeline_run_id", cycle["pipeline_run_id"])

    emit_fn(cycle, event_type, payload)

    if not include_legacy:
        return

    canonical = canonical_event_type(event_type)
    for alias in EVENT_ALIASES.get(canonical, []):
        if alias != event_type:
            emit_fn(cycle, alias, dict(payload))
