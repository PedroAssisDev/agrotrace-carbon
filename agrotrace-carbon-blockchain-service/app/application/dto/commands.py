from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ObserveEventsCommand:
    limit: int = 100


@dataclass(frozen=True, slots=True)
class CreateAnchorRequestCommand:
    source_event_id: str


@dataclass(frozen=True, slots=True)
class BuildEvidencePackageCommand:
    anchor_request_id: UUID | None = None
    source_event_id: str | None = None


@dataclass(frozen=True, slots=True)
class SimulateAnchoringCommand:
    evidence_package_id: UUID
    network_code: str = "local_simulated"


@dataclass(frozen=True, slots=True)
class VerifyEvidencePackageCommand:
    evidence_package_id: UUID


@dataclass(frozen=True, slots=True)
class ReprocessFailedAnchoringCommand:
    limit: int = 50


@dataclass(frozen=True, slots=True)
class GenerateAuditReportCommand:
    anchor_request_id: UUID | None = None
    evidence_package_id: UUID | None = None
