"""Case 4: Boa Vista January revision and reprocessing (v1 → v2)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from demo_config import (  # noqa: E402
    CASE_PREFIX_REVISION,
    FARM_BOA_VISTA,
    RUN_CODE_REVISION,
    YEAR,
    ensure_local_database,
)
from demo_data import REVISION_JANUARY_V1, REVISION_JANUARY_V2  # noqa: E402
from demo_ids import case_id, content_hash_label, idem_key  # noqa: E402
from demo_runner import (  # noqa: E402
    CREATED_SUMMARY,
    log,
    open_uow,
    run_ingestion_chain,
    seed_agents_and_methods,
)
from provenance_service.application.services.provenance_recorder import (  # noqa: E402
    RecordRevisionCommand,
    RecordSourceArtifactRevisionCommand,
)
from provenance_service.domain.shared.enums import CalculationResultSetStatus  # noqa: E402


def main() -> None:
    ensure_local_database()
    case_key = CASE_PREFIX_REVISION.rstrip("_")
    now = datetime.now(timezone.utc)

    uow_factory, recorder = open_uow()
    with uow_factory as uow:
        catalog = seed_agents_and_methods(uow, recorder)

        v1 = run_ingestion_chain(
            uow,
            recorder,
            case_key=f"{case_key}_v1",
            run_code=f"{RUN_CODE_REVISION}-v1",
            farm_reference=FARM_BOA_VISTA,
            reporting_period=f"{YEAR}-01",
            catalog=catalog,
            milk_liters=REVISION_JANUARY_V1,
            granularity="monthly",
            extra_metadata={"revision_version": "v1"},
        )

        rev1 = recorder.record_source_artifact_revision(
            uow,
            RecordSourceArtifactRevisionCommand(
                source_artifact_id=v1.source_artifact_id,
                revision_number=1,
                storage_uri=f"demo://{RUN_CODE_REVISION}/jan_v1.csv",
                content_hash=content_hash_label(f"{case_key}|rev1"),
                received_at=now,
                is_current=False,
                source_artifact_revision_id=case_id(case_key, "artifact_revision", "v1"),
                prov_entity_id=case_id(case_key, "prov_revision_entity", "v1"),
                metadata={"liters": str(REVISION_JANUARY_V1), "version": "v1"},
            ),
        )

        v2 = run_ingestion_chain(
            uow,
            recorder,
            case_key=f"{case_key}_v2",
            run_code=f"{RUN_CODE_REVISION}-v2",
            farm_reference=FARM_BOA_VISTA,
            reporting_period=f"{YEAR}-01",
            catalog=catalog,
            milk_liters=REVISION_JANUARY_V2,
            granularity="monthly",
            parent_pipeline_run_id=v1.pipeline_run_id,
            extra_metadata={"revision_version": "v2", "corrects_run": v1.run_code},
        )

        rev2 = recorder.record_source_artifact_revision(
            uow,
            RecordSourceArtifactRevisionCommand(
                source_artifact_id=v2.source_artifact_id,
                revision_number=2,
                storage_uri=f"demo://{RUN_CODE_REVISION}/jan_v2_corrected.csv",
                content_hash=content_hash_label(f"{case_key}|rev2"),
                received_at=now,
                is_current=True,
                source_artifact_revision_id=case_id(case_key, "artifact_revision", "v2"),
                prov_entity_id=case_id(case_key, "prov_revision_entity", "v2"),
                metadata={"liters": str(REVISION_JANUARY_V2), "version": "v2"},
            ),
        )

        recorder.record_revision(
            uow,
            RecordRevisionCommand(
                previous_entity_id=v1.canonical_prov_entity_id,
                new_entity_id=v2.canonical_prov_entity_id,
                revision_reason="Corrected January milk production from 10000 to 12000 liters",
                metadata={
                    "demo_case": case_key,
                    "idempotency_key": idem_key(case_key, "prov_revision"),
                    "source_artifact_revision_v2": str(rev2.source_artifact_revision_id),
                },
            ),
        )

        uow.commit()

    CREATED_SUMMARY["revision"] = {
        "v1_run_code": v1.run_code,
        "v2_run_code": v2.run_code,
        "revision_v1_id": str(rev1.source_artifact_revision_id),
        "revision_v2_id": str(rev2.source_artifact_revision_id),
        "parent_pipeline_run_id": str(v2.pipeline_run_id),
    }
    log(f"Revision case completed: {v1.run_code} -> {v2.run_code}")
    _ = CalculationResultSetStatus.APPROVED  # noqa: F841 — documents expected status


if __name__ == "__main__":
    main()
