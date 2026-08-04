"""Helpers for blockchain observability: hash scope mapping and event constants."""

from __future__ import annotations

from provenance_service.domain.shared.enums import (
    CANONICALIZATION_METHOD_ALIASES,
    CANONICALIZATION_METHOD_V1,
    HashScope,
    HashSubjectKind,
)

OBSERVABLE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "RAW_DATA_REGISTERED",
        "WRAPPER_EXECUTED",
        "NORMALIZED_BATCH_CREATED",
        "SEMANTIC_MAPPING_COMPLETED",
        "CANONICAL_SNAPSHOT_CREATED",
        "CANONICAL_DATA_PUBLISHED_TO_ONTOLOGY",
        "CALCULATION_STARTED",
        "CALCULATION_PRELIMINARY_RESULT_CREATED",
        "CALCULATION_APPROVED",
        "CALCULATION_REJECTED",
        "APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY",
        "DAILY_DATA_AGGREGATED_TO_MONTHLY",
        "MONTHLY_RESULT_CONSOLIDATED",
        "MONTHLY_DATA_AGGREGATED_TO_ANNUAL",
        "ANNUAL_RESULT_CONSOLIDATED",
        "ANNUAL_RESULT_APPROVED",
        "ANNUAL_RESULT_PUBLISHED_TO_ONTOLOGY",
        "LOCAL_HASH_CREATED",
        "ANCHOR_REQUEST_ELIGIBLE",
    }
)

_HASH_SUBJECT_TO_SCOPE: dict[HashSubjectKind, HashScope] = {
    HashSubjectKind.SOURCE_ARTIFACT: HashScope.RECORD,
    HashSubjectKind.SOURCE_ARTIFACT_REVISION: HashScope.RECORD,
    HashSubjectKind.NORMALIZED_BATCH: HashScope.BATCH,
    HashSubjectKind.CANONICAL_SNAPSHOT: HashScope.SNAPSHOT,
    HashSubjectKind.CALCULATION_RESULT_SET: HashScope.CALCULATION_RESULT,
    HashSubjectKind.CALCULATION_PARAMETER_SET: HashScope.CALCULATION_PARAMETER_SET,
    HashSubjectKind.BUNDLE: HashScope.RECORD,
    HashSubjectKind.OTHER: HashScope.RECORD,
}


def hash_scope_for_subject(subject_kind: HashSubjectKind) -> HashScope:
    return _HASH_SUBJECT_TO_SCOPE.get(subject_kind, HashScope.RECORD)


def default_canonicalization_method() -> str:
    """Emit ``prov_canonical_v1`` for new provenance hash records."""
    return CANONICALIZATION_METHOD_V1


def is_known_canonicalization_method(method: str | None) -> bool:
    """Accept current label and historical ``json_canonical_v1`` alias on read."""
    if not method:
        return False
    return str(method).strip() in CANONICALIZATION_METHOD_ALIASES
