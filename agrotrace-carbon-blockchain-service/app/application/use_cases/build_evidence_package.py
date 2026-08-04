from __future__ import annotations

from app.application.dto.commands import BuildEvidencePackageCommand
from app.application.dto.results import BuildEvidencePackageResult
from app.application.services.evidence_package_builder import EvidencePackageBuilder
from app.domain.entities import HashRecord
from app.domain.ports.provenance_ports import ProvenanceEventReaderPort
from app.domain.value_objects.statuses import (
    AnchorRequestStatus,
    EvidencePackageStatus,
    HashSubjectKind,
)
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.logging.audit_logger import AuditLogger
from app.infrastructure.provenance.sqlite_provenance_event_reader import SQLiteProvenanceDataReader
from app.domain.services.final_publication_gate import require_final_publication_event
from app.shared.clock import utcnow
from app.shared.constants import CANONICALIZATION_METHOD_V1, HASH_ALGORITHM_SHA256
from app.shared.exceptions import InvalidStateError, NotFoundError
from app.shared.ids import new_id


class BuildEvidencePackageUseCase:
    def __init__(
        self,
        uow: SqlAlchemyUnitOfWork,
        data_reader: SQLiteProvenanceDataReader,
        event_reader: ProvenanceEventReaderPort | None = None,
    ) -> None:
        self._uow = uow
        self._data_reader = data_reader
        self._event_reader = event_reader
        self._builder = EvidencePackageBuilder(data_reader)
        self._audit = AuditLogger(uow.audit_logs)

    def execute(self, command: BuildEvidencePackageCommand) -> BuildEvidencePackageResult:
        request = self._resolve_request(command)
        require_final_publication_event(
            request.source_event_type, context="build_evidence_package"
        )
        if request.status not in {
            AnchorRequestStatus.PENDING.value,
            AnchorRequestStatus.BUILDING.value,
            AnchorRequestStatus.FAILED.value,
        }:
            raise InvalidStateError(f"Anchor request status not buildable: {request.status}")

        existing = self._uow.evidence_packages.get_by_anchor_request(request.anchor_request_id)
        if existing and existing.status != EvidencePackageStatus.DRAFT.value:
            return BuildEvidencePackageResult(
                evidence_package_id=existing.evidence_package_id,
                package_hash=existing.package_hash or "",
                merkle_root=existing.merkle_root or "",
            )

        request.status = AnchorRequestStatus.BUILDING.value
        request.updated_at = utcnow()
        self._uow.anchor_requests.update(request)

        event = self._load_event(request.source_event_id)
        package, items = self._builder.build(
            anchor_request_id=request.anchor_request_id,
            event=event,
        )

        self._uow.evidence_packages.add(package)
        self._uow.flush()
        for item in items:
            self._uow.evidence_items.add(item)
            self._uow.hash_records.add(
                HashRecord(
                    hash_record_id=new_id(),
                    subject_kind=HashSubjectKind.EVIDENCE_ITEM.value,
                    subject_id=item.evidence_item_id,
                    hash_algorithm=HASH_ALGORITHM_SHA256,
                    canonicalization_method=CANONICALIZATION_METHOD_V1,
                    hash_value=item.item_hash or "",
                    payload_ref=item.canonical_payload_json,
                    created_at=utcnow(),
                )
            )

        self._uow.hash_records.add(
            HashRecord(
                hash_record_id=new_id(),
                subject_kind=HashSubjectKind.EVIDENCE_PACKAGE.value,
                subject_id=package.evidence_package_id,
                hash_algorithm=HASH_ALGORITHM_SHA256,
                canonicalization_method=CANONICALIZATION_METHOD_V1,
                hash_value=package.package_hash or "",
                payload_ref=package.canonical_payload_json,
                created_at=utcnow(),
            )
        )

        request.status = AnchorRequestStatus.READY.value
        request.updated_at = utcnow()
        self._uow.anchor_requests.update(request)

        self._audit.info(
            event_name="EVIDENCE_PACKAGE_BUILT",
            entity_type="evidence_package",
            entity_id=str(package.evidence_package_id),
            message="Evidence package built successfully",
            correlation_id=request.source_event_id,
            context={
                "package_type": package.package_type,
                "item_count": len(items),
            },
        )

        return BuildEvidencePackageResult(
            evidence_package_id=package.evidence_package_id,
            package_hash=package.package_hash or "",
            merkle_root=package.merkle_root or "",
        )

    def _resolve_request(self, command: BuildEvidencePackageCommand):
        if command.anchor_request_id:
            request = self._uow.anchor_requests.get(command.anchor_request_id)
            if request is None:
                raise NotFoundError(f"Anchor request not found: {command.anchor_request_id}")
            return request
        if command.source_event_id:
            request = self._uow.anchor_requests.get_by_source_event_id(command.source_event_id)
            if request is None:
                raise NotFoundError(f"Anchor request not found for event: {command.source_event_id}")
            return request
        raise ValueError("anchor_request_id or source_event_id is required")

    def _load_event(self, source_event_id: str):
        if self._event_reader is None:
            from app.infrastructure.provenance.sqlite_provenance_event_reader import (
                SQLiteProvenanceEventReader,
            )

            self._event_reader = SQLiteProvenanceEventReader()
        event = self._event_reader.get_event_by_id(source_event_id)
        if event is None:
            raise NotFoundError(f"Provenance event not found: {source_event_id}")
        return event
