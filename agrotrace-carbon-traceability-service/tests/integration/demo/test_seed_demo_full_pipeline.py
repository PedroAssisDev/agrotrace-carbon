"""Integration test: demo seed against configured database (SQLite in CI)."""

from __future__ import annotations

from provenance_service.domain.shared.enums import CalculationResultSetStatus
from provenance_service.infrastructure.config import get_settings
from provenance_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from provenance_service.seed_demo_full_pipeline_001 import RUN_CODE, main


def test_seed_demo_full_pipeline_001_idempotent(db_session_factory) -> None:
    get_settings.cache_clear()  # type: ignore[attr-defined]

    main()
    with SqlAlchemyUnitOfWork(db_session_factory) as uow:
        run = uow.pipeline_runs.get_by_run_code(RUN_CODE)
        assert run is not None
        revs = uow.source_artifact_revisions.list_by_pipeline_run(run.pipeline_run_id)
        assert len(revs) == 1
        wrappers = uow.wrapper_executions.list_by_pipeline_run(run.pipeline_run_id)
        assert len(wrappers) == 1
        assert wrappers[0].input_source_artifact_revision_id == revs[0].source_artifact_revision_id
        rss = uow.calculation_result_sets.list_by_pipeline_run(run.pipeline_run_id)
        assert len(rss) == 1
        assert rss[0].result_set_status is CalculationResultSetStatus.APPROVED
        hashes = uow.hash_records.list_by_pipeline_run(run.pipeline_run_id)
        kinds = {h.subject_kind.value for h in hashes}
        assert "bundle" in kinds
        assert "source_artifact_revision" in kinds

    main()
    with SqlAlchemyUnitOfWork(db_session_factory) as uow2:
        assert uow2.pipeline_runs.get_by_run_code(RUN_CODE) is not None
