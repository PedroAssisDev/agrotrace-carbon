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
class AnchorEvidencePackageResult:
    evidence_package_id: UUID
    network_code: str
    chain_id: int | None
    contract_address: str | None
    evidence_key: str | None
    package_hash: str
    merkle_root: str
    transaction_hash: str | None
    block_number: int | None
    anchoring_status: str
    receipt_status: int | None
    gas_used: int | None
    effective_gas_price: int | None
    explorer_url: str | None
    idempotent_reuse: bool
    anchoring_mode: str
    provider_response: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class QueryAnchoredEvidenceResult:
    found: bool
    evidence_key: str | None
    package_hash: str | None
    merkle_root: str | None
    anchored_at: str | None
    submitter: str | None
    network_code: str
    chain_id: int | None
    contract_address: str | None


@dataclass(frozen=True, slots=True)
class VerifyAnchoredEvidenceResult:
    evidence_package_id: UUID
    offchain_valid: bool
    onchain_found: bool
    package_hash_match: bool
    merkle_root_match: bool
    network_match: bool
    contract_match: bool
    overall_valid: bool
    details: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VerifyEvidencePackageResult:
    evidence_package_id: UUID
    is_valid: bool
    details: dict


@dataclass(frozen=True, slots=True)
class AuditReportResult:
    report: dict
