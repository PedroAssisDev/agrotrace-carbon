#!/usr/bin/env python
"""Seed dos três cenários oficiais de teste.

1. Propriedade com entrada annual direta (annual_report.csv Embrapa)
2. Propriedade com dados monthly (monthly_report.csv Embrapa)
3. Propriedade daily/intraday: daily_report.csv Embrapa (layout intraday:v1)

Os dados passam pela pipeline real até pendência de aprovação (sem mock silencioso).
Samples: agrotrace-carbon-save-file/data/embrapa/ (SAMPLE_DATA_DIR).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = FRONTEND_ROOT.parent
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

import config  # noqa: E402
from services import local_orchestrator as orch  # noqa: E402
from services.bootstrap import bootstrap_all, wipe_all_test_data  # noqa: E402
from services.domain_catalog import OrganizationalGranularity, TemporalGranularity  # noqa: E402
from services.farm_registry_service import resolve_or_register_farm  # noqa: E402
from utils.file_helpers import invalidate_cycle_cache, save_cycle, save_raw_file  # noqa: E402

SCENARIOS = [
    {
        "property_id": "PROP-ANNUAL-001",
        "property_name": "Fazenda Annual Direta",
        "lot_id": "LOT-A-01",
        "animal_id": None,
        "organizational_granularity": OrganizationalGranularity.PROPERTY.value,
        "temporal_granularity": TemporalGranularity.ANNUAL.value,
        "reporting_period": "2024",
        "layout_name": "annual",
        "sample_candidates": ["annual_report.csv"],
    },
    {
        "property_id": "PROP-MONTHLY-001",
        "property_name": "Fazenda Monthly Consolidável",
        "lot_id": "LOT-M-01",
        "animal_id": None,
        "organizational_granularity": OrganizationalGranularity.PROPERTY.value,
        "temporal_granularity": TemporalGranularity.MONTHLY.value,
        "reporting_period": "2026-01",
        "layout_name": "monthly",
        "sample_candidates": ["monthly_report.csv"],
    },
    {
        "property_id": "PROP-DAILY-001",
        "property_name": "Fazenda Daily Consolidável",
        "lot_id": "LOT-D-01",
        "animal_id": "ANIMAL-D-001",
        "organizational_granularity": OrganizationalGranularity.ANIMAL.value,
        "temporal_granularity": TemporalGranularity.DAILY.value,
        "reporting_period": "2021-01-31",
        "layout_name": "intraday",
        "sample_candidates": ["daily_report.csv"],
    },
]


def _resolve_sample(candidates: list[str]) -> Path:
    for name in candidates:
        path = config.SAMPLE_DATA_DIR / name
        if path.exists():
            return path
    # fallback: qualquer csv
    csvs = sorted(config.SAMPLE_DATA_DIR.glob("*.csv"))
    if not csvs:
        raise FileNotFoundError(f"Nenhum CSV em {config.SAMPLE_DATA_DIR}")
    return csvs[0]


def seed_scenario(scenario: dict) -> dict:
    resolve_or_register_farm(
        scenario["property_id"],
        name=scenario["property_name"],
        source="seed_official",
    )
    sample = _resolve_sample(scenario["sample_candidates"])
    # Para layouts annual/monthly, período deve casar com o layout
    period = scenario["reporting_period"]
    layout = scenario["layout_name"]
    if layout == "annual" and len(period) > 4:
        period = period[:4]
    if layout == "monthly" and len(period) == 10:
        period = period[:7]
    if layout == "intraday":
        # wrappers intraday esperam período diário ou usam sample monthly como fallback de arquivo
        name_l = sample.name.lower()
        layout_effective = (
            "intraday"
            if any(token in name_l for token in ("intraday", "diario", "daily"))
            else "monthly"
        )
        if layout_effective == "monthly":
            period = period[:7] if len(period) >= 7 else "2026-01"
            layout = "monthly"
            scenario = {**scenario, "temporal_granularity": TemporalGranularity.MONTHLY.value,
                        "organizational_granularity": OrganizationalGranularity.PROPERTY.value}

    raw_meta = save_raw_file(
        sample,
        property_id=scenario["property_id"],
        reporting_period=period,
    )
    cycle = orch.run_auto_pipeline_after_ingestion(
        raw_meta,
        property_id=scenario["property_id"],
        property_name=scenario["property_name"],
        reporting_period=period,
        layout_name=layout,
        mark_pending=True,
    )
    cycle["lot_id"] = scenario.get("lot_id")
    cycle["animal_id"] = scenario.get("animal_id")
    cycle["organizational_granularity"] = scenario["organizational_granularity"]
    cycle["granularity"] = scenario["temporal_granularity"]
    cycle["seed_scenario"] = scenario["property_id"]
    save_cycle(cycle)
    return cycle


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed dos 3 cenários oficiais")
    parser.add_argument("--wipe-first", action="store_true", help="Reset antes do seed")
    args = parser.parse_args()

    if args.wipe_first:
        wipe_all_test_data(recreate_dbs=True)
        invalidate_cycle_cache()
    else:
        bootstrap_all()

    results = []
    for sc in SCENARIOS:
        print(f"→ Seed {sc['property_id']} ({sc['temporal_granularity']})…")
        try:
            cycle = seed_scenario(sc)
            status = cycle.get("current_status")
            errs = cycle.get("errors") or []
            print(f"  cycle={cycle.get('cycle_id')} status={status} errors={len(errs)}")
            if errs:
                print(f"  last_error={errs[-1]}")
            results.append(cycle)
        except Exception as exc:
            print(f"  FALHA: {exc}")
            return 1

    print(f"Seed concluído: {len(results)} cenários.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
