from __future__ import annotations

from app.application.dto.commands import BuildEvidencePackageCommand, ReprocessFailedAnchoringCommand, SimulateAnchoringCommand
from app.application.use_cases.build_evidence_package import BuildEvidencePackageUseCase
from app.application.use_cases.simulate_anchoring import SimulateAnchoringUseCase
from app.domain.value_objects.statuses import AnchorRequestStatus
from app.infrastructure.anchoring.providers_registry import ProvidersRegistry
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.provenance.sqlite_provenance_event_reader import SQLiteProvenanceDataReader
from app.shared.clock import utcnow


class ReprocessFailedAnchoringUseCase:
    def __init__(
        self,
        uow: SqlAlchemyUnitOfWork,
        data_reader: SQLiteProvenanceDataReader,
        providers: ProvidersRegistry,
    ) -> None:
        self._uow = uow
        self._build = BuildEvidencePackageUseCase(uow, data_reader)
        self._simulate = SimulateAnchoringUseCase(uow, providers)

    def execute(self, command: ReprocessFailedAnchoringCommand) -> list[str]:
        request_ids = self._uow.anchoring_attempts.list_failed_requests(limit=command.limit)
        processed: list[str] = []
        for request_id in request_ids:
            request = self._uow.anchor_requests.get(request_id)
            if request is None:
                continue
            request.status = AnchorRequestStatus.PENDING.value
            request.error_message = None
            request.updated_at = utcnow()
            self._uow.anchor_requests.update(request)

            build_result = self._build.execute(
                BuildEvidencePackageCommand(anchor_request_id=request_id)
            )
            self._simulate.execute(
                SimulateAnchoringCommand(evidence_package_id=build_result.evidence_package_id)
            )
            processed.append(str(request_id))
        return processed
