from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ObserveEventsResult:
    created_request_ids: list[UUID] = field(default_factory=list)
    skipped_event_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BuildEvidencePackageResult:
    evidence_package_id: UUID
    package_hash: str
    merkle_root: str


@dataclass(frozen=True, slots=True)
class SimulateAnchoringResult:
    evidence_package_id: UUID
    transaction_hash: str
    block_number: int
    anchoring_status: str


@dataclass(frozen=True, slots=True)
class VerifyEvidencePackageResult:
    evidence_package_id: UUID
    is_valid: bool
    details: dict


@dataclass(frozen=True, slots=True)
class AuditReportResult:
    report: dict
