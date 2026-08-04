"""Enumerations used both by the domain layer and by the SQL layer.

The string values are stable identifiers that are also used as PostgreSQL
``CREATE TYPE`` enum values. Renaming them is a breaking change.
"""

from __future__ import annotations

from enum import StrEnum


class PipelineRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class WrapperExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ProvBundleType(StrEnum):
    PIPELINE_RUN = "pipeline_run"
    WRAPPER_EXECUTION = "wrapper_execution"
    SEMANTIC_INTEGRATION = "semantic_integration"
    CALCULATION = "calculation"
    PUBLICATION = "publication"
    AUDIT = "audit"


class ProvBundleStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    INVALIDATED = "invalidated"


class ProvEntityType(StrEnum):
    SOURCE_ARTIFACT = "source_artifact"
    SOURCE_ARTIFACT_REVISION = "source_artifact_revision"
    NORMALIZED_BATCH = "normalized_batch"
    CANONICAL_SNAPSHOT = "canonical_snapshot"
    CALCULATION_PARAMETER_SET = "calculation_parameter_set"
    CALCULATION_RESULT_SET = "calculation_result_set"
    ONTOLOGY_RESOURCE = "ontology_resource"
    OTHER = "other"


class ProvActivityType(StrEnum):
    WRAPPER_EXECUTION = "wrapper_execution"
    SEMANTIC_INTEGRATION = "semantic_integration"
    CALCULATION_EXECUTION = "calculation_execution"
    CALCULATION_REVIEW = "calculation_review"
    RESULT_PUBLICATION = "result_publication"
    BLOCKCHAIN_ANCHORING = "blockchain_anchoring"
    OTHER = "other"


class ProvAgentType(StrEnum):
    HUMAN = "human"
    SOFTWARE = "software"
    ORGANIZATION = "organization"


class SemanticExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PublicationStage(StrEnum):
    DRAFT = "draft"
    PRELIMINARY = "preliminary"
    CANONICAL_INPUT = "canonical_input"
    FINAL = "final"
    PUBLICATION_FINAL = "publication_final"
    RETRACTED = "retracted"


class CalculationMethodStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ParameterSetStatus(StrEnum):
    DRAFT = "draft"
    LOCKED = "locked"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class CalculationExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CalculationResultSetStatus(StrEnum):
    PRELIMINARY = "preliminary"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class CalculationResultType(StrEnum):
    EMISSION_TOTAL = "emission_total"
    EMISSION_BY_CATEGORY = "emission_by_category"
    INTENSITY = "intensity"
    PRODUCTIVITY = "productivity"
    GHG_EMISSION = "ghg_emission"
    CARBON_FOOTPRINT = "carbon_footprint"
    OTHER = "other"


class CalculationReviewDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class ResultPublicationStatus(StrEnum):
    PENDING = "pending"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class HashAlgorithm(StrEnum):
    SHA256 = "sha256"
    SHA3_256 = "sha3_256"


class HashSubjectKind(StrEnum):
    SOURCE_ARTIFACT = "source_artifact"
    SOURCE_ARTIFACT_REVISION = "source_artifact_revision"
    NORMALIZED_BATCH = "normalized_batch"
    CANONICAL_SNAPSHOT = "canonical_snapshot"
    CALCULATION_RESULT_SET = "calculation_result_set"
    CALCULATION_PARAMETER_SET = "calculation_parameter_set"
    BUNDLE = "bundle"
    OTHER = "other"


class BlockchainAnchorStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    PUBLISHED = "published"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


class PeriodGranularity(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"
    ANNUAL = "annual"
    CUSTOM = "custom"


class ReportingPeriodStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    CONSOLIDATED = "consolidated"
    APPROVED = "approved"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"


class ResultScope(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"
    ANNUAL = "annual"
    CUSTOM = "custom"


class ConsolidationType(StrEnum):
    DIRECT = "direct"
    DAILY_TO_MONTHLY = "daily_to_monthly"
    MONTHLY_TO_ANNUAL = "monthly_to_annual"
    MANUAL_ADJUSTMENT = "manual_adjustment"
    REPROCESSING = "reprocessing"


class AggregationType(StrEnum):
    DAILY_TO_MONTHLY = "daily_to_monthly"
    MONTHLY_TO_ANNUAL = "monthly_to_annual"
    MANUAL_GROUPING = "manual_grouping"


class HashScope(StrEnum):
    RECORD = "record"
    BATCH = "batch"
    SNAPSHOT = "snapshot"
    CALCULATION_RESULT = "calculation_result"
    CALCULATION_PARAMETER_SET = "calculation_parameter_set"
    CALCULATION_REVIEW = "calculation_review"
    ONTOLOGY_PUBLICATION = "ontology_publication"
    AGGREGATION = "aggregation"


class RunType(StrEnum):
    RAW_DATA_INGESTION = "raw_data_ingestion"
    DAILY_INGESTION = "daily_ingestion"
    MONTHLY_CALCULATION = "monthly_calculation"
    ANNUAL_CALCULATION = "annual_calculation"
    DAILY_TO_MONTHLY_AGGREGATION = "daily_to_monthly_aggregation"
    MONTHLY_TO_ANNUAL_AGGREGATION = "monthly_to_annual_aggregation"
    MANUAL_REPROCESSING = "manual_reprocessing"


class AnchorMode(StrEnum):
    LOCAL_SIMULATION = "local_simulation"
    TESTNET = "testnet"
    MAINNET = "mainnet"
    PERMISSIONED_NETWORK = "permissioned_network"


CANONICALIZATION_METHOD_V1 = "prov_canonical_v1"
# Alias de leitura para registros históricos gravados com o rótulo antigo
# (algoritmo do traceability nunca foi o json_canonical_v1 do blockchain-service).
CANONICALIZATION_METHOD_LEGACY_ALIAS = "json_canonical_v1"
CANONICALIZATION_METHOD_ALIASES = frozenset(
    {CANONICALIZATION_METHOD_V1, CANONICALIZATION_METHOD_LEGACY_ALIAS}
)
