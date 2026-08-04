"""Case 3: Fazenda Santa Clara — daily January → monthly → annual."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from demo_config import (  # noqa: E402
    CASE_PREFIX_DAILY,
    FARM_SANTA_CLARA,
    YEAR,
    ensure_local_database,
)
from demo_data import (  # noqa: E402
    SANTA_CLARA_DAILY_MILK_LITERS,
    SANTA_CLARA_JANUARY_DAYS,
    SANTA_CLARA_JANUARY_TOTAL,
    SANTA_CLARA_OTHER_MONTHLY,
)
from demo_ids import (  # noqa: E402
    run_code_annual_santa,
    run_code_daily_january,
    run_code_monthly_aggregate_santa,
)
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
    case_key = CASE_PREFIX_DAILY.rstrip("_")
    daily_entities: list = []
    daily_run_codes: list[str] = []

    uow_factory, recorder = open_uow()
    with uow_factory as uow:
        catalog = seed_agents_and_methods(uow, recorder)

        for day in range(1, SANTA_CLARA_JANUARY_DAYS + 1):
            rc = run_code_daily_january(day)
            daily_run_codes.append(rc)
            r = run_ingestion_chain(
                uow,
                recorder,
                case_key=case_key,
                run_code=rc,
                farm_reference=FARM_SANTA_CLARA,
                reporting_period=f"{YEAR}-01-{day:02d}",
                catalog=catalog,
                milk_liters=SANTA_CLARA_DAILY_MILK_LITERS,
                granularity="daily",
            )
            daily_entities.append(r.canonical_prov_entity_id)

        log(f"  created {len(daily_run_codes)} daily runs for January")

        jan_monthly = record_temporal_aggregation(
            uow,
            recorder,
            case_key=case_key,
            run_code=run_code_monthly_aggregate_santa(1),
            farm_reference=FARM_SANTA_CLARA,
            reporting_period=f"{YEAR}-01",
            catalog=catalog,
            aggregation_kind="monthly_aggregation_january",
            source_snapshot_entity_ids=daily_entities,
            total_milk_liters=SANTA_CLARA_JANUARY_TOTAL,
            source_run_codes=daily_run_codes,
        )

        monthly_entities = [jan_monthly.canonical_prov_entity_id]
        monthly_run_codes = [jan_monthly.run_code]

        for month, liters in sorted(SANTA_CLARA_OTHER_MONTHLY.items()):
            rc = run_code_monthly_aggregate_santa(month)
            monthly_run_codes.append(rc)
            r = run_ingestion_chain(
                uow,
                recorder,
                case_key=case_key,
                run_code=rc,
                farm_reference=FARM_SANTA_CLARA,
                reporting_period=f"{YEAR}-{month:02d}",
                catalog=catalog,
                milk_liters=liters,
                granularity="monthly",
                extra_metadata={"representative_monthly_aggregate": True},
            )
            monthly_entities.append(r.canonical_prov_entity_id)

        annual_total = SANTA_CLARA_JANUARY_TOTAL + sum(SANTA_CLARA_OTHER_MONTHLY.values())
        annual = record_temporal_aggregation(
            uow,
            recorder,
            case_key=case_key,
            run_code=run_code_annual_santa(),
            farm_reference=FARM_SANTA_CLARA,
            reporting_period=YEAR,
            catalog=catalog,
            aggregation_kind="annual_aggregation",
            source_snapshot_entity_ids=monthly_entities,
            total_milk_liters=annual_total,
            source_run_codes=monthly_run_codes,
        )
        uow.commit()

    CREATED_SUMMARY["daily_to_monthly_to_annual"] = {
        "january_daily_count": len(daily_run_codes),
        "monthly_aggregate_count": len(monthly_entities),
        "annual_run_code": annual.run_code,
        "annual_pipeline_run_id": str(annual.pipeline_run_id),
    }
    log(
        f"Case daily->monthly->annual: {len(daily_run_codes)} daily + "
        f"{len(monthly_entities)} monthly aggregates + {annual.run_code}"
    )


if __name__ == "__main__":
    main()
