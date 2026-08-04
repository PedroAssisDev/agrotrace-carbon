from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordSourceArtifactCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.pipeline.entities import SourceArtifact


class RegisterSourceArtifact:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordSourceArtifactCommand) -> SourceArtifact:
        with self._uow_factory() as uow:
            artifact = self._recorder.record_source_artifact(uow, cmd)
            uow.commit()
            return artifact
