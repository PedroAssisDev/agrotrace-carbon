"""List pipeline runs with filters and pagination."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.pipeline.entities import PipelineRun


@dataclass(slots=True)
class ListPipelineRunsQuery:
    limit: int = 50
    offset: int = 0
    run_status: str | None = None
    farm_reference: str | None = None
    started_from: datetime | None = None
    started_to: datetime | None = None


@dataclass(slots=True)
class ListPipelineRunsResult:
    items: list[PipelineRun]
    total: int
    limit: int
    offset: int


class ListPipelineRuns:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, query: ListPipelineRunsQuery) -> ListPipelineRunsResult:
        with self._uow_factory() as uow:
            items, total = uow.pipeline_runs.list_filtered(
                limit=query.limit,
                offset=query.offset,
                run_status=query.run_status,
                farm_reference=query.farm_reference,
                started_from=query.started_from,
                started_to=query.started_to,
            )
            return ListPipelineRunsResult(
                items=items,
                total=total,
                limit=query.limit,
                offset=query.offset,
            )
