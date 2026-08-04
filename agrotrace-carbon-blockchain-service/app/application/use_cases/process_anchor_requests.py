from __future__ import annotations

from app.application.dto.commands import BuildEvidencePackageCommand
from app.application.use_cases.build_evidence_package import BuildEvidencePackageUseCase
from app.domain.value_objects.statuses import AnchorRequestStatus
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.provenance.sqlite_provenance_event_reader import SQLiteProvenanceDataReader


class ProcessAnchorRequestsUseCase:
    def __init__(self, uow: SqlAlchemyUnitOfWork, data_reader: SQLiteProvenanceDataReader) -> None:
        self._uow = uow
        self._build = BuildEvidencePackageUseCase(uow, data_reader)

    def execute(self, *, limit: int = 100) -> list[str]:
        requests = self._uow.anchor_requests.list_by_status(AnchorRequestStatus.PENDING.value, limit=limit)
        package_ids: list[str] = []
        for request in requests:
            result = self._build.execute(
                BuildEvidencePackageCommand(anchor_request_id=request.anchor_request_id)
            )
            package_ids.append(str(result.evidence_package_id))
        return package_ids
