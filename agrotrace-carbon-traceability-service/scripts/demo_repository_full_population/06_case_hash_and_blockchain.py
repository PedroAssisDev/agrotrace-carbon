"""Case 5: Complement hashes and simulated blockchain anchors + demo audit events."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from demo_config import DEMO_PREFIX, RUN_CODE_ANNUAL, ensure_local_database  # noqa: E402
from demo_ids import content_hash_label  # noqa: E402
from demo_runner import (  # noqa: E402
    CREATED_SUMMARY,
    log,
    open_uow,
    record_demo_audit_event,
    seed_agents_and_methods,
)
from provenance_service.application.services.provenance_recorder import (  # noqa: E402
    ProvenanceRecorder,
    RecordBlockchainAnchorCommand,
    RecordHashCommand,
)
from provenance_service.application.unit_of_work import UnitOfWork  # noqa: E402
from provenance_service.domain.shared.enums import (  # noqa: E402
    BlockchainAnchorStatus,
    HashSubjectKind,
)


def _anchor_if_missing(
    uow: UnitOfWork,
    recorder: ProvenanceRecorder,
    *,
    pipeline_run_id: UUID,
    hash_record_id: UUID,
    label: str,
) -> None:
    anchors = uow.blockchain_anchors.list_by_pipeline_run(pipeline_run_id)
    if any(a.hash_record_id == hash_record_id for a in anchors):
        return
    recorder.record_blockchain_anchor(
        uow,
        RecordBlockchainAnchorCommand(
            pipeline_run_id=pipeline_run_id,
            hash_record_id=hash_record_id,
            blockchain_network="demo-chain",
            anchor_status=BlockchainAnchorStatus.CONFIRMED,
            transaction_hash=f"demo-tx-{label}",
            metadata={"simulated": True, "chain_name": "demo-chain"},
        ),
    )


def main() -> None:
    ensure_local_database()
    anchored = 0
    uow_factory, recorder = open_uow()
    with uow_factory as uow:
        catalog = seed_agents_and_methods(uow, recorder)
        runs, _total = uow.pipeline_runs.list_filtered(limit=500, offset=0)
        demo_runs = [r for r in runs if r.run_code.startswith(DEMO_PREFIX)]

        for run in demo_runs:
            arts = uow.source_artifacts.list_by_pipeline_run(run.pipeline_run_id)
            for art in arts:
                existing = uow.hash_records.find_by_subject(
                    HashSubjectKind.SOURCE_ARTIFACT.value,
                    art.source_artifact_id,
                    "sha256",
                )
                if existing is None:
                    hr = recorder.record_hash(
                        uow,
                        RecordHashCommand(
                            pipeline_run_id=run.pipeline_run_id,
                            subject_kind=HashSubjectKind.SOURCE_ARTIFACT,
                            subject_id=art.source_artifact_id,
                            hash_value=art.content_hash
                            or content_hash_label(f"artifact|{art.source_artifact_id}"),
                            prov_entity_id=art.prov_entity_id,
                            metadata={"demo": "complement_source_artifact_hash"},
                        ),
                    )
                    _anchor_if_missing(
                        uow,
                        recorder,
                        pipeline_run_id=run.pipeline_run_id,
                        hash_record_id=hr.hash_record_id,
                        label=f"sa-{art.source_artifact_id}",
                    )
                    anchored += 1

            pubs = uow.result_publication_executions.list_by_pipeline_run(run.pipeline_run_id)
            for pub in pubs:
                rs = uow.calculation_result_sets.get(pub.calculation_result_set_id)
                if rs is not None:
                    hr = uow.hash_records.find_by_subject(
                        HashSubjectKind.CALCULATION_RESULT_SET.value,
                        rs.calculation_result_set_id,
                        "sha256",
                    )
                    if hr is not None:
                        _anchor_if_missing(
                            uow,
                            recorder,
                            pipeline_run_id=run.pipeline_run_id,
                            hash_record_id=hr.hash_record_id,
                            label=f"pub-{pub.result_publication_execution_id}",
                        )
                record_demo_audit_event(
                    uow,
                    event_type="demo.publication.verified",
                    subject_kind="result_publication_execution",
                    subject_id=pub.result_publication_execution_id,
                    actor_agent_id=catalog.agent_system_id,
                    payload={"run_code": run.run_code, "simulated": True},
                )

        record_demo_audit_event(
            uow,
            event_type="demo.hash_and_blockchain.completed",
            subject_kind="pipeline_run",
            subject_id=demo_runs[0].pipeline_run_id if demo_runs else UUID(int=0),
            actor_agent_id=catalog.agent_system_id,
            payload={"demo_run_count": len(demo_runs), "complemented_anchors": anchored},
        )
        uow.commit()

    CREATED_SUMMARY["hash_blockchain"] = {
        "demo_runs_processed": len(demo_runs) if demo_runs else 0,
        "complemented_source_hashes": anchored,
        "sample_run": RUN_CODE_ANNUAL,
    }
    log(f"Hash/blockchain complement: {len(demo_runs)} demo runs, {anchored} new source hashes")


if __name__ == "__main__":
    main()
