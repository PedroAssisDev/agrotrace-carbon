from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordCanonicalSnapshotCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.semantic.entities import CanonicalSnapshot


class RegisterCanonicalSnapshot:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordCanonicalSnapshotCommand) -> CanonicalSnapshot:
        with self._uow_factory() as uow:
            snapshot = self._recorder.record_canonical_snapshot(uow, cmd)
            uow.commit()
            return snapshot
