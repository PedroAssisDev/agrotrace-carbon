"""Case 1: Fazenda São Pedro — annual direct (no aggregation)."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from demo_config import (  # noqa: E402
    CASE_PREFIX_ANNUAL,
    FARM_SAO_PEDRO,
    RUN_CODE_ANNUAL,
    YEAR,
    ensure_local_database,
)
from demo_data import SAO_PEDRO_ANNUAL  # noqa: E402
from demo_runner import (  # noqa: E402
    CREATED_SUMMARY,
    log,
    open_uow,
    run_ingestion_chain,
    seed_agents_and_methods,
)


def main() -> None:
    ensure_local_database()
    uow_factory, recorder = open_uow()
    with uow_factory as uow:
        catalog = seed_agents_and_methods(uow, recorder)
        result = run_ingestion_chain(
            uow,
            recorder,
            case_key=CASE_PREFIX_ANNUAL.rstrip("_"),
            run_code=RUN_CODE_ANNUAL,
            farm_reference=FARM_SAO_PEDRO,
            reporting_period=YEAR,
            catalog=catalog,
            milk_liters=SAO_PEDRO_ANNUAL["milk_liters"],
            granularity="annual",
            extra_metadata={
                "energy_kwh": str(SAO_PEDRO_ANNUAL["energy_kwh"]),
                "lactating_cows_avg": str(SAO_PEDRO_ANNUAL["lactating_cows_avg"]),
                "area_ha": str(SAO_PEDRO_ANNUAL["area_ha"]),
            },
        )
        uow.commit()

    CREATED_SUMMARY["annual_direct"] = {
        "pipeline_run_id": str(result.pipeline_run_id),
        "run_code": result.run_code,
        "canonical_snapshot_id": str(result.canonical_snapshot_id),
        "calculation_result_set_id": str(result.calculation_result_set_id),
    }
    log(f"Case annual direct completed: {RUN_CODE_ANNUAL}")


if __name__ == "__main__":
    main()
