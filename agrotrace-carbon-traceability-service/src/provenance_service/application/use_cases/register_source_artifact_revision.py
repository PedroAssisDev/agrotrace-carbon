"""Register a new revision of a source artifact."""

from __future__ import annotations

from provenance_service.application.services.provenance_recorder import (
    ProvenanceRecorder,
    RecordSourceArtifactRevisionCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.pipeline.entities import SourceArtifactRevision


class RegisterSourceArtifactRevision:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        recorder: ProvenanceRecorder,
    ) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordSourceArtifactRevisionCommand) -> SourceArtifactRevision:
        with self._uow_factory() as uow:
            revision = self._recorder.record_source_artifact_revision(uow, cmd)
            uow.commit()
            return revision
