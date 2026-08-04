from __future__ import annotations

from provenance_service.application.services import (
    ProvenanceRecorder,
    RecordSemanticIntegrationCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.semantic.entities import SemanticIntegrationExecution


class RegisterSemanticIntegration:
    def __init__(self, uow_factory: UnitOfWorkFactory, recorder: ProvenanceRecorder) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(self, cmd: RecordSemanticIntegrationCommand) -> SemanticIntegrationExecution:
        with self._uow_factory() as uow:
            integration = self._recorder.record_semantic_integration(uow, cmd)
            uow.commit()
            return integration
