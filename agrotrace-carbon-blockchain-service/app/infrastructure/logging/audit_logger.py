from __future__ import annotations

import json

from app.domain.entities import AuditLogEntry
from app.domain.ports.repositories_ports import AuditLogRepositoryPort
from app.domain.value_objects.statuses import AuditSeverity
from app.shared.clock import utcnow
from app.shared.ids import new_id


class AuditLogger:
    def __init__(self, repository: AuditLogRepositoryPort) -> None:
        self._repository = repository

    def info(
        self,
        *,
        event_name: str,
        entity_type: str,
        entity_id: str,
        message: str,
        correlation_id: str | None = None,
        context: dict | None = None,
    ) -> None:
        self._repository.add(
            AuditLogEntry(
                audit_log_id=new_id(),
                event_name=event_name,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                severity=AuditSeverity.INFO.value,
                message=message,
                context_json=json.dumps(context or {}, ensure_ascii=False),
                created_at=utcnow(),
            )
        )

    def error(
        self,
        *,
        event_name: str,
        entity_type: str,
        entity_id: str,
        message: str,
        correlation_id: str | None = None,
        context: dict | None = None,
    ) -> None:
        self._repository.add(
            AuditLogEntry(
                audit_log_id=new_id(),
                event_name=event_name,
                entity_type=entity_type,
                entity_id=entity_id,
                correlation_id=correlation_id,
                severity=AuditSeverity.ERROR.value,
                message=message,
                context_json=json.dumps(context or {}, ensure_ascii=False),
                created_at=utcnow(),
            )
        )
