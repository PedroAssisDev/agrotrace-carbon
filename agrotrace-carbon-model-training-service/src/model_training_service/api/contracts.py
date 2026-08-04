"""Contratos tipados da API programática de treinamento."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from model_training_service.domain.enums import (
    Granularity,
    ModelAvailabilityStatus,
    ModelFamily,
    ModelScope,
    Target,
    TrainingMode,
    TrainingRunStatus,
    VersionStatus,
)


@dataclass(frozen=True)
class ModelSlot:
    family: str
    scope: str
    granularity: str
    target: str
    property_id: str | None = None

    def logical_key(self) -> str:
        if self.family == ModelFamily.REGRESSION.value:
            return f"regression|{self.granularity}|{self.target}|global"
        return f"time_series|monthly|{self.property_id}|{self.target}"

    def label(self) -> str:
        if self.family == ModelFamily.REGRESSION.value:
            return f"regression/{self.granularity}/global/{self.target}"
        return f"time_series/monthly/{self.property_id}/{self.target}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ModelSlot":
        return cls(
            family=str(payload["family"]),
            scope=str(payload["scope"]),
            granularity=str(payload["granularity"]),
            target=str(payload["target"]),
            property_id=payload.get("property_id"),
        )


@dataclass
class TrainModelsRequest:
    property_id: str
    mode: str = TrainingMode.ENSURE_MISSING.value
    slots: list[ModelSlot] = field(default_factory=list)
    candidate_profile: str = "core"
    selection_metric: str = "mae"
    minimum_improvement_over_baseline: float = 0.0
    activate_after_success: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "property_id": self.property_id,
            "mode": self.mode,
            "slots": [slot.to_dict() for slot in self.slots],
            "candidate_profile": self.candidate_profile,
            "selection_metric": self.selection_metric,
            "minimum_improvement_over_baseline": self.minimum_improvement_over_baseline,
            "activate_after_success": self.activate_after_success,
        }


@dataclass
class ModelAvailabilityItem:
    family: str
    scope: str
    property_id: str | None
    granularity: str
    target: str
    status: str
    eligible: bool
    active_model_id: str | None = None
    active_version: str | None = None
    created_at: str | None = None
    training_period_start: str | None = None
    training_period_end: str | None = None
    record_count: int | None = None
    algorithm: str | None = None
    selection_metric: str | None = None
    selection_score: float | None = None
    reason: str | None = None
    stale: bool = False
    artifact_dir: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DataSummary:
    monthly_records: int = 0
    annual_records: int = 0
    last_monthly_period: str | None = None
    last_annual_period: str | None = None
    property_monthly_records: int = 0
    property_annual_records: int = 0
    property_last_monthly_period: str | None = None
    min_ts_records: int = 12

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ModelAvailabilityReport:
    property_id: str
    data_summary: DataSummary
    models: list[ModelAvailabilityItem] = field(default_factory=list)
    active_training_runs: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str | None = None
    source_ok: bool = True
    source_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "property_id": self.property_id,
            "data_summary": self.data_summary.to_dict(),
            "models": [item.to_dict() for item in self.models],
            "active_training_runs": list(self.active_training_runs),
            "updated_at": self.updated_at,
            "source_ok": self.source_ok,
            "source_error": self.source_error,
        }


@dataclass
class TrainingRunRecord:
    run_id: str
    property_id: str
    mode: str
    status: str
    current_stage: str
    requested_models: list[dict[str, Any]] = field(default_factory=list)
    configuration: dict[str, Any] = field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    models_created: list[dict[str, Any]] = field(default_factory=list)
    models_failed: list[dict[str, Any]] = field(default_factory=list)
    models_skipped: list[dict[str, Any]] = field(default_factory=list)
    models_ineligible: list[dict[str, Any]] = field(default_factory=list)
    error_summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Re-export enums used by consumers
__all__ = [
    "ModelSlot",
    "TrainModelsRequest",
    "ModelAvailabilityItem",
    "DataSummary",
    "ModelAvailabilityReport",
    "TrainingRunRecord",
    "Granularity",
    "ModelFamily",
    "ModelScope",
    "Target",
    "TrainingMode",
    "ModelAvailabilityStatus",
    "VersionStatus",
    "TrainingRunStatus",
]
