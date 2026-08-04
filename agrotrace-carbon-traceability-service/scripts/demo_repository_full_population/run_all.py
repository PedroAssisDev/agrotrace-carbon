"""Orchestrate full demo repository population."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from demo_config import ensure_local_database  # noqa: E402
from demo_runner import CREATED_SUMMARY, log  # noqa: E402

_STEPS = (
    "01_seed_agents_and_methods",
    "02_case_annual_direct",
    "03_case_monthly_to_annual",
    "04_case_daily_to_monthly_to_annual",
    "05_case_revision_and_reprocessing",
    "06_case_hash_and_blockchain",
)


def _run_module(name: str) -> None:
    log(f"=== {name} ===")
    mod = importlib.import_module(name)
    mod.main()


def main() -> int:
    ensure_local_database()
    for step in _STEPS:
        _run_module(step)

    import validate_full_population as validate_mod  # noqa: E402

    log("=== validate_full_population ===")
    if validate_mod.main() != 0:
        return 1

    import table_coverage_report as coverage_mod  # noqa: E402

    log("=== table_coverage_report ===")
    coverage_mod.main()

    log("=== SUMMARY ===")
    for key, value in CREATED_SUMMARY.items():
        log(f"  {key}: {value}")

    log("Full demo population completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
