"""Audit-context HTTP routes (3 endpoints)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from provenance_service.application.services import (
    RecordBlockchainAnchorCommand,
    RecordHashCommand,
)
from provenance_service.application.use_cases import (
    ComputeAndRecordHash,
    ListOutboxEvents,
    ListOutboxEventsQuery,
    RegisterBlockchainAnchor,
    VerifyIntegrity,
)
from provenance_service.interfaces.api.deps import (
    provide_compute_and_record_hash,
    provide_list_outbox_events,
    provide_register_blockchain_anchor,
    provide_verify_integrity,
)
from provenance_service.interfaces.api.schemas.audit import (
    BlockchainAnchorResponse,
    HashCheckResultResponse,
    HashRecordResponse,
    IntegrityReportResponse,
    OutboxEventListResponse,
    OutboxEventResponse,
    RegisterBlockchainAnchorRequest,
    RegisterHashRecordRequest,
)
router = APIRouter(tags=["audit"])


@router.post(
    "/hash-records",
    response_model=HashRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_hash_record(
    payload: RegisterHashRecordRequest,
    use_case: Annotated[
        ComputeAndRecordHash, Depends(provide_compute_and_record_hash)
    ],
) -> HashRecordResponse:
    cmd = RecordHashCommand(**payload.model_dump())
    record = use_case.execute(cmd)
    return HashRecordResponse.model_validate(record)


@router.post(
    "/blockchain-anchors",
    response_model=BlockchainAnchorResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_blockchain_anchor(
    payload: RegisterBlockchainAnchorRequest,
    use_case: Annotated[
        RegisterBlockchainAnchor, Depends(provide_register_blockchain_anchor)
    ],
) -> BlockchainAnchorResponse:
    cmd = RecordBlockchainAnchorCommand(**payload.model_dump())
    anchor = use_case.execute(cmd)
    return BlockchainAnchorResponse.model_validate(anchor)


@router.get(
    "/audit/verify/{bundle_id}",
    response_model=IntegrityReportResponse,
)
def verify_bundle_integrity(
    bundle_id: UUID,
    use_case: Annotated[VerifyIntegrity, Depends(provide_verify_integrity)],
) -> IntegrityReportResponse:
    report = use_case.execute(bundle_id)
    return IntegrityReportResponse(
        bundle_id=report.bundle_id,
        pipeline_run_id=report.pipeline_run_id,
        is_valid=report.is_valid,
        checks=[HashCheckResultResponse.model_validate(c) for c in report.checks],
        missing_subjects=list(report.missing_subjects),
        unsupported_subjects=list(report.unsupported_subjects),
    )


@router.get(
    "/audit/outbox-events",
    response_model=OutboxEventListResponse,
)
def list_outbox_events(
    use_case: Annotated[ListOutboxEvents, Depends(provide_list_outbox_events)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    aggregate_kind: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
) -> OutboxEventListResponse:
    result = use_case.execute(
        ListOutboxEventsQuery(
            limit=limit,
            offset=offset,
            status=status_filter,
            aggregate_kind=aggregate_kind,
            event_type=event_type,
        )
    )
    return OutboxEventListResponse(
        items=[OutboxEventResponse.model_validate(e) for e in result.items],
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )
