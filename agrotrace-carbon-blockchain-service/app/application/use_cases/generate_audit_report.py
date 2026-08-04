from __future__ import annotations

from app.application.dto.commands import GenerateAuditReportCommand
from app.application.dto.results import AuditReportResult
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.exceptions import NotFoundError


class GenerateAuditReportUseCase:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow

    def execute(self, command: GenerateAuditReportCommand) -> AuditReportResult:
        if command.evidence_package_id:
            package = self._uow.evidence_packages.get(command.evidence_package_id)
            if package is None:
                raise NotFoundError(f"Evidence package not found: {command.evidence_package_id}")
            request = self._uow.anchor_requests.get(package.anchor_request_id)
            entity_type = "evidence_package"
            entity_id = str(package.evidence_package_id)
        elif command.anchor_request_id:
            request = self._uow.anchor_requests.get(command.anchor_request_id)
            if request is None:
                raise NotFoundError(f"Anchor request not found: {command.anchor_request_id}")
            package = self._uow.evidence_packages.get_by_anchor_request(request.anchor_request_id)
            entity_type = "anchor_request"
            entity_id = str(request.anchor_request_id)
        else:
            raise ValueError("anchor_request_id or evidence_package_id is required")

        logs = self._uow.audit_logs.list_for_entity(entity_type, entity_id)
        tx = (
            self._uow.blockchain_transactions.get_latest_for_package(package.evidence_package_id)
            if package
            else None
        )
        items = (
            self._uow.evidence_items.list_by_package(package.evidence_package_id)
            if package
            else []
        )

        report = {
            "anchor_request": None if request is None else {
                "anchor_request_id": str(request.anchor_request_id),
                "source_event_id": request.source_event_id,
                "source_event_type": request.source_event_type,
                "status": request.status,
            },
            "evidence_package": None if package is None else {
                "evidence_package_id": str(package.evidence_package_id),
                "package_type": package.package_type,
                "package_hash": package.package_hash,
                "merkle_root": package.merkle_root,
                "status": package.status,
                "item_count": len(items),
            },
            "blockchain_transaction": None if tx is None else {
                "transaction_hash": tx.transaction_hash,
                "block_number": tx.block_number,
                "anchoring_status": tx.anchoring_status,
            },
            "audit_log": [
                {
                    "event_name": log.event_name,
                    "severity": log.severity,
                    "message": log.message,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ],
        }
        return AuditReportResult(report=report)
