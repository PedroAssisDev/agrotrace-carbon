"""Seed shared agents, calculation method and wrapper definition."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from demo_config import ensure_local_database  # noqa: E402
from demo_runner import CREATED_SUMMARY, log, open_uow, seed_agents_and_methods  # noqa: E402


def main() -> None:
    ensure_local_database()
    uow_factory, recorder = open_uow()
    with uow_factory as uow:
        catalog = seed_agents_and_methods(uow, recorder)
        uow.commit()
    CREATED_SUMMARY["catalog"] = {
        "agent_trigger_id": str(catalog.agent_trigger_id),
        "agent_reviewer_id": str(catalog.agent_reviewer_id),
        "calculation_method_id": str(catalog.calculation_method_id),
        "wrapper_definition_id": str(catalog.wrapper_definition_id),
    }
    log("Seed agents and methods completed.")


if __name__ == "__main__":
    main()
