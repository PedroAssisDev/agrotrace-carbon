"""Case 2: Fazenda Boa Vista — 12 monthly runs aggregated to annual."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from demo_config import (  # noqa: E402
    CASE_PREFIX_MONTHLY,
    FARM_BOA_VISTA,
    YEAR,
    ensure_local_database,
)
from demo_data import BOA_VISTA_ANNUAL_TOTAL, BOA_VISTA_MONTHLY_MILK_LITERS  # noqa: E402
from demo_ids import run_code_annual_boa_vista, run_code_monthly  # noqa: E402
from demo_runner import (  # noqa: E402
    CREATED_SUMMARY,
    log,
    open_uow,
    record_temporal_aggregation,
    run_ingestion_chain,
    seed_agents_and_methods,
)


def main() -> None:
    ensure_local_database()
    case_key = CASE_PREFIX_MONTHLY.rstrip("_")
    monthly_entities: list = []
    monthly_run_codes: list[str] = []

    uow_factory, recorder = open_uow()
    with uow_factory as uow:
        catalog = seed_agents_and_methods(uow, recorder)

        for month, liters in sorted(BOA_VISTA_MONTHLY_MILK_LITERS.items()):
            rc = run_code_monthly(month)
            monthly_run_codes.append(rc)
            r = run_ingestion_chain(
                uow,
                recorder,
                case_key=case_key,
                run_code=rc,
                farm_reference=FARM_BOA_VISTA,
                reporting_period=f"{YEAR}-{month:02d}",
                catalog=catalog,
                milk_liters=liters,
                granularity="monthly",
            )
            monthly_entities.append(r.canonical_prov_entity_id)
            log(f"  monthly {month:02d}: {rc} ({liters} L)")

        annual = record_temporal_aggregation(
            uow,
            recorder,
            case_key=case_key,
            run_code=run_code_annual_boa_vista(),
            farm_reference=FARM_BOA_VISTA,
            reporting_period=YEAR,
            catalog=catalog,
            aggregation_kind="annual_aggregation",
            source_snapshot_entity_ids=monthly_entities,
            total_milk_liters=BOA_VISTA_ANNUAL_TOTAL,
            source_run_codes=monthly_run_codes,
        )
        uow.commit()

    CREATED_SUMMARY["monthly_to_annual"] = {
        "monthly_run_count": len(monthly_run_codes),
        "annual_run_code": annual.run_code,
        "annual_pipeline_run_id": str(annual.pipeline_run_id),
        "expected_total_liters": str(BOA_VISTA_ANNUAL_TOTAL),
        "aggregation_inputs": len(monthly_entities),
    }
    log(
        f"Case monthly->annual completed: {len(monthly_run_codes)} months + "
        f"{annual.run_code} (total {BOA_VISTA_ANNUAL_TOTAL} L)"
    )


if __name__ == "__main__":
    main()
