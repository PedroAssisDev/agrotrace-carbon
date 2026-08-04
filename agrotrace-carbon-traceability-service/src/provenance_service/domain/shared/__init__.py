"""Shared domain primitives: ids, hashing, time, enums, errors and value objects.

Importing from this package must NEVER pull SQLAlchemy, FastAPI or any
infrastructure module. The domain layer is framework-agnostic.
"""

from provenance_service.domain.shared.enums import (
    BlockchainAnchorStatus,
    CalculationExecutionStatus,
    CalculationMethodStatus,
    CalculationResultSetStatus,
    CalculationResultType,
    CalculationReviewDecision,
    HashAlgorithm,
    HashSubjectKind,
    OutboxStatus,
    ParameterSetStatus,
    PipelineRunStatus,
    ProvActivityType,
    ProvAgentType,
    ProvBundleStatus,
    ProvBundleType,
    ProvEntityType,
    PublicationStage,
    ResultPublicationStatus,
    SemanticExecutionStatus,
    WrapperExecutionStatus,
)
from provenance_service.domain.shared.errors import (
    AlreadyExistsError,
    AppendOnlyViolationError,
    DomainError,
    IdempotencyConflictError,
    InvariantViolationError,
    NotFoundError,
)
from provenance_service.domain.shared.hashing import (
    canonicalize,
    compute_hash,
    compute_hash_hex,
)
from provenance_service.domain.shared.ids import new_uuid7
from provenance_service.domain.shared.time import utcnow
from provenance_service.domain.shared.types import (
    BusinessKey,
    Hash,
    IdempotencyKey,
)

__all__ = [
    "AlreadyExistsError",
    "AppendOnlyViolationError",
    "BlockchainAnchorStatus",
    "BusinessKey",
    "CalculationExecutionStatus",
    "CalculationMethodStatus",
    "CalculationResultSetStatus",
    "CalculationResultType",
    "CalculationReviewDecision",
    "DomainError",
    "Hash",
    "HashAlgorithm",
    "HashSubjectKind",
    "IdempotencyConflictError",
    "IdempotencyKey",
    "InvariantViolationError",
    "NotFoundError",
    "OutboxStatus",
    "ParameterSetStatus",
    "PipelineRunStatus",
    "ProvActivityType",
    "ProvAgentType",
    "ProvBundleStatus",
    "ProvBundleType",
    "ProvEntityType",
    "PublicationStage",
    "ResultPublicationStatus",
    "SemanticExecutionStatus",
    "WrapperExecutionStatus",
    "canonicalize",
    "compute_hash",
    "compute_hash_hex",
    "new_uuid7",
    "utcnow",
]
