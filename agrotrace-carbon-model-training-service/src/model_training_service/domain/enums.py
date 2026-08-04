from enum import StrEnum


class Granularity(StrEnum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class Target(StrEnum):
    MILK_PRODUCTION = "milk_production_liters"
    TOTAL_EMISSIONS = "total_ghg_emissions_tco2e"


class ModelFamily(StrEnum):
    REGRESSION = "regression"
    TIME_SERIES = "time_series"


class ModelScope(StrEnum):
    GLOBAL = "global"
    PROPERTY = "property"


class TrainingMode(StrEnum):
    ENSURE_MISSING = "ensure_missing"
    RETRAIN_STALE = "retrain_stale"
    RETRAIN_SELECTED = "retrain_selected"


class ModelAvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    INELIGIBLE = "ineligible"
    STALE = "stale"
    TRAINING = "training"
    FAILED = "failed"


class VersionStatus(StrEnum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    REJECTED = "rejected"
    FAILED = "failed"
    ARCHIVED = "archived"


class TrainingRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
