"""Register a standalone ontology resource link via :class:`ProvenanceRecorder`."""

from __future__ import annotations

from provenance_service.application.services.provenance_recorder import (
    ProvenanceRecorder,
    RecordOntologyResourceLinkCommand,
)
from provenance_service.application.use_cases._base import UnitOfWorkFactory
from provenance_service.domain.semantic.entities import OntologyResourceLink

# Backward-compatible alias for routers and tests.
RegisterOntologyResourceLinkCommand = RecordOntologyResourceLinkCommand


class RegisterOntologyResourceLink:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        recorder: ProvenanceRecorder,
    ) -> None:
        self._uow_factory = uow_factory
        self._recorder = recorder

    def execute(
        self, cmd: RecordOntologyResourceLinkCommand
    ) -> OntologyResourceLink:
        with self._uow_factory() as uow:
            link = self._recorder.record_ontology_resource_link(uow, cmd)
            uow.commit()
            return link
