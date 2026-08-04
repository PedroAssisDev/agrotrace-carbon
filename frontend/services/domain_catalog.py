"""Fonte única de vocabulário de domínio do protótipo (FE + orquestração).

Granularidades temporais canônicas: daily | monthly | annual.
Granularidades organizacionais: animal | lot | property.
Eventos: uma emissão por fato; aliases apenas na leitura.
"""

from __future__ import annotations

from enum import Enum
from typing import Final


class TemporalGranularity(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    ANNUAL = "annual"


class OrganizationalGranularity(str, Enum):
    ANIMAL = "animal"
    LOT = "lot"
    PROPERTY = "property"


# Aliases de leitura → canônico (nunca emitir o alias)
TEMPORAL_ALIASES: Final[dict[str, TemporalGranularity]] = {
    "daily": TemporalGranularity.DAILY,
    "intraday": TemporalGranularity.DAILY,
    "day": TemporalGranularity.DAILY,
    "diario": TemporalGranularity.DAILY,
    "diário": TemporalGranularity.DAILY,
    "monthly": TemporalGranularity.MONTHLY,
    "mensal": TemporalGranularity.MONTHLY,
    "month": TemporalGranularity.MONTHLY,
    "annual": TemporalGranularity.ANNUAL,
    "anual": TemporalGranularity.ANNUAL,
    "yearly": TemporalGranularity.ANNUAL,
    "year": TemporalGranularity.ANNUAL,
}

ORG_ALIASES: Final[dict[str, OrganizationalGranularity]] = {
    "animal": OrganizationalGranularity.ANIMAL,
    "lot": OrganizationalGranularity.LOT,
    "lote": OrganizationalGranularity.LOT,
    "property": OrganizationalGranularity.PROPERTY,
    "farm": OrganizationalGranularity.PROPERTY,
    "fazenda": OrganizationalGranularity.PROPERTY,
    "rural_property": OrganizationalGranularity.PROPERTY,
}


def _temporal_key(value: object) -> str:
    """Extrai rótulo canônico; ``str(str.Enum)`` pode ser ``'TemporalGranularity.ANNUAL'``."""
    if isinstance(value, TemporalGranularity):
        return value.value
    if isinstance(value, Enum) and not isinstance(value, bool):
        raw = getattr(value, "value", value)
        return str(raw).strip().lower()
    return str(value).strip().lower()


def normalize_temporal(
    value: str | TemporalGranularity | None,
    *,
    default: TemporalGranularity = TemporalGranularity.MONTHLY,
) -> TemporalGranularity:
    if value is None:
        return default
    if isinstance(value, TemporalGranularity):
        return value
    key = _temporal_key(value)
    if not key:
        return default
    if key in TEMPORAL_ALIASES:
        return TEMPORAL_ALIASES[key]
    upper = key.upper()
    if upper == "MONTHLY":
        return TemporalGranularity.MONTHLY
    if upper in {"YEARLY", "ANNUAL"}:
        return TemporalGranularity.ANNUAL
    if upper == "DAILY":
        return TemporalGranularity.DAILY
    return default


def temporal_to_calc_scope(granularity: TemporalGranularity | str) -> str:
    """Mapeia canônico FE → valor aceito pelo calculation-service (TemporalScope)."""
    # Não usar isinstance(..., str) em str.Enum — membros são str e quebram .value.
    g = granularity if isinstance(granularity, TemporalGranularity) else normalize_temporal(granularity)
    if g == TemporalGranularity.MONTHLY:
        return "monthly"
    if g == TemporalGranularity.DAILY:
        return "monthly"  # calc service não tem daily; consolidação é explícita a montante
    return "annual"  # TemporalScope.ANNUAL no calculation-service


def calc_scope_to_canonical(scope: str | TemporalGranularity | None) -> TemporalGranularity:
    """YEARLY/monthly do calculation-service → annual/monthly canônico."""
    return normalize_temporal(scope, default=TemporalGranularity.MONTHLY)


def normalize_organizational(
    value: str | OrganizationalGranularity | None,
    *,
    default: OrganizationalGranularity = OrganizationalGranularity.PROPERTY,
) -> OrganizationalGranularity:
    if value is None:
        return default
    if isinstance(value, OrganizationalGranularity):
        return value
    if isinstance(value, Enum):
        key = str(getattr(value, "value", value)).strip().lower()
    else:
        key = str(value).strip().lower()
    if not key:
        return default
    return ORG_ALIASES.get(key, default)


# ── Eventos canônicos (emissão única) ────────────────────────────────────────
class PipelineEventType(str, Enum):
    RAW_DATA_UPLOADED = "RAW_DATA_UPLOADED"
    ORIGINAL_FILE_STORED = "ORIGINAL_FILE_STORED"
    RAW_FILE_HASH_CREATED = "RAW_FILE_HASH_CREATED"
    RAW_DATA_REGISTERED = "RAW_DATA_REGISTERED"
    WRAPPER_EXECUTED = "WRAPPER_EXECUTED"
    NORMALIZED_BATCH_CREATED = "NORMALIZED_BATCH_CREATED"
    SEMANTIC_MAPPING_COMPLETED = "SEMANTIC_MAPPING_COMPLETED"
    SEMANTIC_VALIDATION_COMPLETED = "SEMANTIC_VALIDATION_COMPLETED"
    CALCULATION_PRELIMINARY_RESULT_CREATED = "CALCULATION_PRELIMINARY_RESULT_CREATED"
    CALCULATION_APPROVED = "CALCULATION_APPROVED"
    CALCULATION_REJECTED = "CALCULATION_REJECTED"
    CYCLE_APPROVED = "CYCLE_APPROVED"
    APPROVED_RESULT_PUBLISHED = "APPROVED_RESULT_PUBLISHED"
    MONTHLY_RESULT_CONSOLIDATED = "MONTHLY_RESULT_CONSOLIDATED"
    ANNUAL_RESULT_CONSOLIDATED = "ANNUAL_RESULT_CONSOLIDATED"
    EVIDENCE_PACKAGE_CREATED = "EVIDENCE_PACKAGE_CREATED"
    BLOCKCHAIN_ANCHORED = "BLOCKCHAIN_ANCHORED"
    INTEGRITY_VERIFIED = "INTEGRITY_VERIFIED"
    PIPELINE_STEP_FAILED = "PIPELINE_STEP_FAILED"


# Leitura: legado → canônico (não emitir legado)
EVENT_READ_ALIASES: Final[dict[str, str]] = {
    "RAW_DATA_RECEIVED": "RAW_DATA_UPLOADED",
    "FINAL_ONTOLOGY_PUBLISHED": "APPROVED_RESULT_PUBLISHED",
    "FINAL_ONTOLOGY_PUBLICATION_STARTED": "APPROVED_RESULT_PUBLISHED",
    "CANONICAL_PUBLISHED": "SEMANTIC_MAPPING_COMPLETED",
    "CANONICAL_MODEL_POPULATED": "SEMANTIC_MAPPING_COMPLETED",
    "PRELIMINARY_RESULT_CREATED": "CALCULATION_PRELIMINARY_RESULT_CREATED",
    "CALCULATION_EXECUTED": "CALCULATION_PRELIMINARY_RESULT_CREATED",
    "LOCAL_HASH_CREATED": "EVIDENCE_PACKAGE_CREATED",
    "MERKLE_ROOT_CREATED": "EVIDENCE_PACKAGE_CREATED",
    "ANCHORING_SIMULATED": "BLOCKCHAIN_ANCHORED",
    "BLOCKCHAIN_ANCHOR_CREATED": "BLOCKCHAIN_ANCHORED",
    "ANCHOR_REQUEST_CREATED": "BLOCKCHAIN_ANCHORED",
    "VERIFICATION_EXECUTED": "INTEGRITY_VERIFIED",
    "INTEGRITY_VERIFICATION_EXECUTED": "INTEGRITY_VERIFIED",
    "PROVENANCE_CHAIN_VERIFIED": "INTEGRITY_VERIFIED",
    "FILE_CALCULATION_APPROVED": "CYCLE_APPROVED",
    "CALCULATION_APPROVED": "CALCULATION_APPROVED",
}


def canonical_event(event_type: str) -> str:
    return EVENT_READ_ALIASES.get(event_type, event_type)


def is_publication_event(event_type: str) -> bool:
    c = canonical_event(event_type)
    return c == PipelineEventType.APPROVED_RESULT_PUBLISHED.value or event_type in {
        "APPROVED_RESULT_PUBLISHED",
        "FINAL_ONTOLOGY_PUBLISHED",
    }


# ── Status ───────────────────────────────────────────────────────────────────
PUBLICATION_STATUSES = ("PENDING", "PUBLISHED", "FAILED")
REVIEW_ITEM_APPROVED = frozenset({
    "APPROVED",
    "APPROVED_WITH_ZERO",
    "APPROVED_WITH_MANUAL_ADJUSTMENT",
})

# Gate / milestone names still used in cycle.current_status
PUBLICATION_MILESTONE = "APPROVED_RESULT_PUBLISHED"
# Alias kept for cycles already persisted
PUBLICATION_MILESTONE_LEGACY = "FINAL_ONTOLOGY_PUBLISHED"
