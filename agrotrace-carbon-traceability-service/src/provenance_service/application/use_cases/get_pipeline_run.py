"""Fetch a single pipeline run."""

from __future__ import annotations

from uuid import UUID

from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.pipeline.entities import PipelineRun
from provenance_service.domain.shared.errors import NotFoundError


class GetPipelineRun:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, pipeline_run_id: UUID) -> PipelineRun:
        with self._uow_factory() as uow:
            run = uow.pipeline_runs.get(pipeline_run_id)
            if run is None:
                raise NotFoundError(f"PipelineRun {pipeline_run_id} not found")
            return run
