from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordBlockchainAnchorCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.audit.entities import BlockchainAnchor


class RegisterBlockchainAnchor:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordBlockchainAnchorCommand) -> BlockchainAnchor:
        with self._uow_factory() as uow:
            anchor = self._recorder.record_blockchain_anchor(uow, cmd)
            uow.commit()
            return anchor
