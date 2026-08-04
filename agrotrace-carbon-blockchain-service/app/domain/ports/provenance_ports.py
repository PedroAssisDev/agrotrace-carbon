from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProvenanceEvent:
    outbox_event_id: str
    event_type: str
    status: str
    created_at: datetime
    payload: dict
    pipeline_run_id: UUID | None
    calculation_execution_id: UUID | None
    calculation_result_set_id: UUID | None
    reporting_period_id: UUID | None
    source_table: str | None
    source_record_id: UUID | None


@dataclass(frozen=True, slots=True)
class ReportingPeriodData:
    reporting_period_id: UUID
    period_start: datetime
    period_end: datetime
    period_granularity: str
    period_label: str


@dataclass(frozen=True, slots=True)
class PipelineRunData:
    pipeline_run_id: UUID
    farm_id_hash: str | None
    project_id_hash: str | None
    reporting_period_id: UUID | None


@dataclass(frozen=True, slots=True)
class CalculationResultSetData:
    calculation_result_set_id: UUID
    pipeline_run_id: UUID
    calculation_execution_id: UUID
    summary_hash: str | None
    result_scope: str | None
    consolidation_type: str | None
    reporting_period_id: UUID | None
    approved_at: datetime | None
    published_at: datetime | None


@dataclass(frozen=True, slots=True)
class HashRecordData:
    hash_record_id: UUID
    subject_kind: str
    subject_id: UUID
    hash_value: str
    hash_scope: str | None
    canonicalization_method: str | None


@dataclass(frozen=True, slots=True)
class AggregationLinkData:
    aggregation_link_id: UUID
    parent_result_set_id: UUID
    child_result_set_id: UUID
    aggregation_type: str


class ProvenanceEventReaderPort(ABC):
    @abstractmethod
    def fetch_pending_events(
        self,
        *,
        event_types: set[str],
        after_created_at: datetime | None = None,
        limit: int = 100,
    ) -> list[ProvenanceEvent]:
        raise NotImplementedError

    @abstractmethod
    def get_event_by_id(self, outbox_event_id: str) -> ProvenanceEvent | None:
        raise NotImplementedError


class ProvenanceDataReaderPort(ABC):
    @abstractmethod
    def get_reporting_period(self, reporting_period_id: UUID) -> ReportingPeriodData | None:
        raise NotImplementedError

    @abstractmethod
    def get_pipeline_run(self, pipeline_run_id: UUID) -> PipelineRunData | None:
        raise NotImplementedError

    @abstractmethod
    def get_calculation_result_set(
        self, calculation_result_set_id: UUID
    ) -> CalculationResultSetData | None:
        raise NotImplementedError

    @abstractmethod
    def get_hash_records_for_subject(
        self, subject_kind: str, subject_id: UUID
    ) -> list[HashRecordData]:
        raise NotImplementedError

    @abstractmethod
    def get_aggregation_link_by_id(self, link_id: UUID) -> AggregationLinkData | None:
        raise NotImplementedError

    @abstractmethod
    def get_calculation_execution_method_version_hash(
        self, calculation_execution_id: UUID
    ) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def get_calculation_execution_parameter_set_hash(
        self, calculation_execution_id: UUID
    ) -> str | None:
        raise NotImplementedError
