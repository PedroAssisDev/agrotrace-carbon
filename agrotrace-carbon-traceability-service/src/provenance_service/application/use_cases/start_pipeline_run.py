from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    StartPipelineRunCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.pipeline.entities import PipelineRun


class StartPipelineRun:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: StartPipelineRunCommand) -> PipelineRun:
        with self._uow_factory() as uow:
            run = self._recorder.start_pipeline_run(uow, cmd)
            uow.commit()
            return run
