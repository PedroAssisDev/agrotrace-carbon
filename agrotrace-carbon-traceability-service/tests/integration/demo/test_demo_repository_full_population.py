"""Integration test: full demo repository population against SQLite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DEMO = ROOT / "scripts" / "demo_repository_full_population"

if str(SCRIPTS_DEMO) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DEMO))


@pytest.mark.integration
def test_demo_repository_full_population_run_all(db_session_factory) -> None:
    from provenance_service.infrastructure.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    import run_all as run_all_mod  # noqa: PLC0415

    assert run_all_mod.main() == 0

    import validate_full_population as validate_mod  # noqa: PLC0415

    assert validate_mod.main() == 0

    from demo_config import (  # noqa: PLC0415
        DEMO_PREFIX,
        RUN_CODE_ANNUAL,
        RUN_CODE_REVISION,
    )
    from demo_ids import run_code_annual_boa_vista, run_code_monthly  # noqa: PLC0415
    from provenance_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

    with SqlAlchemyUnitOfWork(db_session_factory) as uow:
        assert uow.pipeline_runs.get_by_run_code(RUN_CODE_ANNUAL) is not None
        assert uow.pipeline_runs.get_by_run_code(run_code_annual_boa_vista()) is not None
        assert uow.pipeline_runs.get_by_run_code(run_code_monthly(1)) is not None
        assert uow.pipeline_runs.get_by_run_code(f"{RUN_CODE_REVISION}-v2") is not None

        runs, _ = uow.pipeline_runs.list_filtered(limit=500, offset=0)
        demo_runs = [r for r in runs if r.run_code.startswith(DEMO_PREFIX)]
        assert len(demo_runs) >= 4

        assert uow.hash_records.list_by_pipeline_run(demo_runs[0].pipeline_run_id)
        anchors = []
        for r in demo_runs:
            anchors.extend(uow.blockchain_anchors.list_by_pipeline_run(r.pipeline_run_id))
        assert anchors

        revs = uow.prov_relations.list_revisions_for_pipeline_run(
            uow.pipeline_runs.get_by_run_code(f"{RUN_CODE_REVISION}-v2").pipeline_run_id  # type: ignore[union-attr]
        )
        assert len(revs) >= 1


@pytest.mark.integration
def test_table_coverage_report_finds_expected_tables(db_session_factory) -> None:
    from provenance_service.infrastructure.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    import run_all as run_all_mod  # noqa: PLC0415
    import table_coverage_report as coverage_mod  # noqa: PLC0415
    from demo_tables import EXPECTED_TABLES  # noqa: PLC0415
    from sqlalchemy import inspect, text

    from demo_config import create_session_stack  # noqa: PLC0415

    run_all_mod.main()

    engine, _, _ = create_session_stack()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    with engine.connect() as conn:
        for name in EXPECTED_TABLES:
            assert name in tables
            count = conn.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar()
            assert int(count or 0) > 0, f"expected rows in {name}"

    assert coverage_mod.main() == 0
    engine.dispose()
