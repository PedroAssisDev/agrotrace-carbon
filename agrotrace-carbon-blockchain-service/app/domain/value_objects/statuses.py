from __future__ import annotations

from enum import StrEnum


class AnchorRequestStatus(StrEnum):
    PENDING = "pending"
    BUILDING = "building"
    READY = "ready"
    ANCHORING = "anchoring"
    ANCHORED = "anchored"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RequestScope(StrEnum):
    MONTHLY = "monthly"
    ANNUAL = "annual"
    AGGREGATION = "aggregation"
    MANUAL = "manual"


class EvidencePackageStatus(StrEnum):
    DRAFT = "draft"
    HASHED = "hashed"
    READY_TO_ANCHOR = "ready_to_anchor"
    ANCHORING = "anchoring"
    ANCHORED = "anchored"
    VERIFIED = "verified"
    VERIFICATION_FAILED = "verification_failed"


class EvidenceItemType(StrEnum):
    CALCULATION_METHOD_VERSION = "calculation_method_version"
    PARAMETER_SET = "parameter_set"
    APPROVED_RESULT = "approved_result"
    PUBLICATION_RECEIPT = "publication_receipt"
    LOCAL_HASH_REF = "local_hash_ref"
    AGGREGATION_LINK = "aggregation_link"


class HashSubjectKind(StrEnum):
    EVIDENCE_ITEM = "evidence_item"
    EVIDENCE_PACKAGE = "evidence_package"
    ANCHOR_PAYLOAD = "anchor_payload"
    METADATA = "metadata"


class AnchoringMode(StrEnum):
    SIMULATED = "simulated"
    REAL = "real"


class AnchoringStatus(StrEnum):
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    SIMULATED = "simulated"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class AttemptStatus(StrEnum):
    STARTED = "started"
    SIMULATED = "simulated"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class VerificationType(StrEnum):
    ITEM_HASH = "item_hash"
    PACKAGE_HASH = "package_hash"
    MERKLE_ROOT = "merkle_root"
    FULL = "full"


class AuditSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
