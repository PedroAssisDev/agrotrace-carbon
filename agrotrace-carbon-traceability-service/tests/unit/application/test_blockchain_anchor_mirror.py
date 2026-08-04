"""Unit tests for blockchain anchor mirror + integrity verification on ProvenanceRecorder."""

from __future__ import annotations

from uuid import uuid4

import pytest

from provenance_service.application.services.provenance_recorder import (
    ConfirmBlockchainAnchorCommand,
    ProvenanceRecorder,
    RecordBlockchainAnchorCommand,
    RecordHashCommand,
    RecordIntegrityVerificationCommand,
    StartPipelineRunCommand,
)
from provenance_service.domain.shared.enums import (
    BlockchainAnchorStatus,
    HashAlgorithm,
    HashSubjectKind,
)
from tests.unit.application.fakes import FakeUnitOfWork


@pytest.fixture
def recorder() -> ProvenanceRecorder:
    return ProvenanceRecorder()


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _pipeline_and_hash(recorder, uow):
    run = recorder.start_pipeline_run(
        uow,
        StartPipelineRunCommand(
            run_code=f"RUN-{uuid4().hex[:8]}",
            farm_reference="FARM-1",
            reporting_period_reference="2026-01",
        ),
    )
    subject_id = uuid4()
    hash_record = recorder.record_hash(
        uow,
        RecordHashCommand(
            pipeline_run_id=run.pipeline_run_id,
            subject_kind=HashSubjectKind.BUNDLE,
            subject_id=subject_id,
            hash_value="a" * 64,
            hash_algorithm=HashAlgorithm.SHA256,
        ),
    )
    return run, hash_record


def test_record_blockchain_anchor_populates_package_fields(recorder, uow) -> None:
    run, hash_record = _pipeline_and_hash(recorder, uow)
    anchor = recorder.record_blockchain_anchor(
        uow,
        RecordBlockchainAnchorCommand(
            pipeline_run_id=run.pipeline_run_id,
            hash_record_id=hash_record.hash_record_id,
            blockchain_network="local_simulated",
            anchor_status=BlockchainAnchorStatus.PENDING,
            evidence_package_external_id="ep-1",
            package_hash="b" * 64,
            merkle_root="c" * 64,
            anchor_provider="frontend",
            anchor_mode="local_simulation",
            metadata={
                "cycle_id": "CYC-1",
                "publication_id": "PUB-1",
                "request_id": "req-1",
            },
        ),
    )
    assert anchor.evidence_package_external_id == "ep-1"
    assert anchor.package_hash == "b" * 64
    assert anchor.merkle_root == "c" * 64
    assert anchor.anchor_status is BlockchainAnchorStatus.PENDING
    pending = [e for e in uow.outbox.items.values() if e.event_type == "blockchain_anchor.pending"]
    assert pending
    assert pending[-1].pipeline_run_id == run.pipeline_run_id
    assert pending[-1].payload.get("evidence_package_id") == "ep-1"


def test_record_blockchain_anchor_idempotent_by_request(recorder, uow) -> None:
    run, hash_record = _pipeline_and_hash(recorder, uow)
    cmd = RecordBlockchainAnchorCommand(
        pipeline_run_id=run.pipeline_run_id,
        hash_record_id=hash_record.hash_record_id,
        blockchain_network="local_simulated",
        evidence_package_external_id="ep-idem",
        package_hash="d" * 64,
        metadata={"request_id": "same-req"},
    )
    a1 = recorder.record_blockchain_anchor(uow, cmd)
    a2 = recorder.record_blockchain_anchor(uow, cmd)
    assert a1.blockchain_anchor_id == a2.blockchain_anchor_id
    assert len(uow.blockchain_anchors.list_by_pipeline_run(run.pipeline_run_id)) == 1


def test_confirm_blockchain_anchor_updates_and_is_idempotent(recorder, uow) -> None:
    run, hash_record = _pipeline_and_hash(recorder, uow)
    pending = recorder.record_blockchain_anchor(
        uow,
        RecordBlockchainAnchorCommand(
            pipeline_run_id=run.pipeline_run_id,
            hash_record_id=hash_record.hash_record_id,
            blockchain_network="ethereum_sepolia",
            evidence_package_external_id="ep-confirm",
            package_hash="e" * 64,
            metadata={"request_id": "r1", "cycle_id": "C1"},
        ),
    )
    confirmed = recorder.confirm_blockchain_anchor(
        uow,
        ConfirmBlockchainAnchorCommand(
            blockchain_anchor_id=pending.blockchain_anchor_id,
            transaction_hash="0x" + "ab" * 32,
            chain_id="11155111",
            block_number="12345",
            metadata={
                "contract_address": "0xcontract",
                "receipt_status": "1",
                "event_identifier": "Anchored(bytes32)",
            },
        ),
    )
    assert confirmed.anchor_status is BlockchainAnchorStatus.CONFIRMED
    assert confirmed.transaction_hash == "0x" + "ab" * 32
    assert confirmed.chain_id == "11155111"
    again = recorder.confirm_blockchain_anchor(
        uow,
        ConfirmBlockchainAnchorCommand(
            evidence_package_external_id="ep-confirm",
            pipeline_run_id=run.pipeline_run_id,
            transaction_hash="0x" + "ab" * 32,
        ),
    )
    assert again.blockchain_anchor_id == confirmed.blockchain_anchor_id


def test_integrity_verification_match_and_idempotent(recorder, uow) -> None:
    run, hash_record = _pipeline_and_hash(recorder, uow)
    anchor = recorder.record_blockchain_anchor(
        uow,
        RecordBlockchainAnchorCommand(
            pipeline_run_id=run.pipeline_run_id,
            hash_record_id=hash_record.hash_record_id,
            blockchain_network="local_simulated",
            evidence_package_external_id="ep-ver",
            package_hash="f" * 64,
        ),
    )
    ev1 = recorder.record_integrity_verification(
        uow,
        RecordIntegrityVerificationCommand(
            pipeline_run_id=run.pipeline_run_id,
            blockchain_anchor_id=anchor.blockchain_anchor_id,
            verification_id="ver-1",
            result="match",
            local_values={"merkle_root": "f" * 64},
            recovered_values={"merkle_root": "f" * 64},
            metadata={"cycle_id": "C1"},
        ),
    )
    ev2 = recorder.record_integrity_verification(
        uow,
        RecordIntegrityVerificationCommand(
            pipeline_run_id=run.pipeline_run_id,
            blockchain_anchor_id=anchor.blockchain_anchor_id,
            verification_id="ver-1",
            result="match",
            local_values={"merkle_root": "f" * 64},
            recovered_values={"merkle_root": "f" * 64},
        ),
    )
    assert ev1.audit_event_id == ev2.audit_event_id
    assert ev1.event_type == "integrity_verification.match"


def test_integrity_verification_divergence(recorder, uow) -> None:
    run, hash_record = _pipeline_and_hash(recorder, uow)
    anchor = recorder.record_blockchain_anchor(
        uow,
        RecordBlockchainAnchorCommand(
            pipeline_run_id=run.pipeline_run_id,
            hash_record_id=hash_record.hash_record_id,
            blockchain_network="local_simulated",
            evidence_package_external_id="ep-div",
            package_hash="1" * 64,
        ),
    )
    ev = recorder.record_integrity_verification(
        uow,
        RecordIntegrityVerificationCommand(
            pipeline_run_id=run.pipeline_run_id,
            blockchain_anchor_id=anchor.blockchain_anchor_id,
            verification_id="ver-div",
            result="divergence",
            local_values={"merkle_root": "1" * 64},
            recovered_values={"merkle_root": "2" * 64},
        ),
    )
    assert ev.event_type == "integrity_verification.divergence"
