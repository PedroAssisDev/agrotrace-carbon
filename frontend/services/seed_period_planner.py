"""Planejamento de entradas de dados e grupos de aprovação para o seed.

DEPRECATED: delega a save_file.emulated.planner para compatibilidade.
"""

from __future__ import annotations

import sys
import warnings
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Iterator

import config

SAVE_FILE_ROOT = config.SAVE_FILE_SERVICE_DIR
if str(SAVE_FILE_ROOT) not in sys.path:
    sys.path.insert(0, str(SAVE_FILE_ROOT))

from save_file.emulated.planner import (  # noqa: E402
    PlannedApprovalGroup as _PlannedApprovalGroup,
    PlannedEntry as _PlannedEntry,
    build_entry_id,
    expected_approval_count,
    expected_entry_count,
    group_daily_by_month,
    iter_days,
    plan_all,
)


@dataclass(frozen=True)
class SeedDataEntry:
    entry_id: str
    scenario_key: str
    property_id: str
    property_name: str
    data_granularity: str
    period_key: str
    reporting_period: str
    approval_group_key: str
    layout: str
    index: int
    year: int | None = None
    month: int | None = None
    day: date | None = None


@dataclass
class SeedApprovalGroup:
    cycle_id: str
    scenario_key: str
    property_id: str
    property_name: str
    reporting_period: str
    approval_granularity: str
    data_granularity: str
    layout: str
    approval_group_key: str
    coverage_label: str
    entries: list[SeedDataEntry] = field(default_factory=list)
    index: int = 1


@dataclass
class SeedScenarioPlan:
    scenario_key: str
    property_id: str
    property_name: str
    data_granularity: str
    approval_granularity: str
    layout: str
    entry_prefix: str
    entries: list[SeedDataEntry] = field(default_factory=list)
    approval_groups: list[SeedApprovalGroup] = field(default_factory=list)


def _to_seed_entry(e: _PlannedEntry) -> SeedDataEntry:
    return SeedDataEntry(
        entry_id=e.entry_id,
        scenario_key=e.scenario_key,
        property_id=e.property_id,
        property_name=e.property_name,
        data_granularity=e.data_granularity,
        period_key=e.period_key,
        reporting_period=e.reporting_period,
        approval_group_key=e.approval_group_key,
        layout=e.layout,
        index=e.index,
        year=e.year,
        month=e.month,
        day=e.day,
    )


def _to_seed_group(g: _PlannedApprovalGroup) -> SeedApprovalGroup:
    return SeedApprovalGroup(
        cycle_id=g.cycle_id,
        scenario_key=g.scenario_key,
        property_id=g.property_id,
        property_name=g.property_name,
        reporting_period=g.reporting_period,
        approval_granularity=g.approval_granularity,
        data_granularity=g.data_granularity,
        layout=g.layout,
        approval_group_key=g.approval_group_key,
        coverage_label=g.coverage_label,
        entries=[_to_seed_entry(e) for e in g.entries],
        index=g.index,
    )


def build_all_seed_plans(profile_mode: str = "demo") -> list[SeedScenarioPlan]:
    warnings.warn(
        "seed_period_planner.build_all_seed_plans está deprecated",
        DeprecationWarning,
        stacklevel=2,
    )
    profiles, _, groups = plan_all(profile_mode)
    by_scenario: dict[str, SeedScenarioPlan] = {}
    for profile in profiles:
        for scenario in profile.scenarios:
            by_scenario[scenario.scenario_key] = SeedScenarioPlan(
                scenario_key=scenario.scenario_key,
                property_id=profile.property_id,
                property_name=profile.name,
                data_granularity=scenario.data_granularity,
                approval_granularity=scenario.approval_granularity,
                layout=scenario.layout,
                entry_prefix=scenario.entry_prefix,
            )
    for g in groups:
        plan = by_scenario[g.scenario_key]
        plan.entries.extend(_to_seed_group(g).entries)
        plan.approval_groups.append(_to_seed_group(g))
    return list(by_scenario.values())


def all_data_entries(plans: list[SeedScenarioPlan] | None = None) -> list[SeedDataEntry]:
    plans = plans or build_all_seed_plans()
    return [entry for plan in plans for entry in plan.entries]


def all_approval_groups(plans: list[SeedScenarioPlan] | None = None) -> list[SeedApprovalGroup]:
    plans = plans or build_all_seed_plans()
    return [group for plan in plans for group in plan.approval_groups]


def entry_to_dict(entry: SeedDataEntry) -> dict[str, Any]:
    return {
        "entry_id": entry.entry_id,
        "scenario_key": entry.scenario_key,
        "property_id": entry.property_id,
        "property_name": entry.property_name,
        "data_granularity": entry.data_granularity,
        "period_key": entry.period_key,
        "reporting_period": entry.reporting_period,
        "approval_group_key": entry.approval_group_key,
        "layout": entry.layout,
        "index": entry.index,
    }


# Compat: funções nomeadas do seed legado
def plan_monthly_boa_vista() -> SeedScenarioPlan:
    return next(p for p in build_all_seed_plans() if p.scenario_key == "monthly_boa_vista")


def plan_annual_santa_clara() -> SeedScenarioPlan:
    return next(p for p in build_all_seed_plans() if p.scenario_key == "annual_santa_clara")


def plan_daily_experimental() -> SeedScenarioPlan:
    """Diário desativado temporariamente no catálogo demo."""
    plans = [p for p in build_all_seed_plans() if p.scenario_key == "daily_experimental"]
    if not plans:
        raise RuntimeError(
            "Cenário daily_experimental desativado. "
            "Reative FARM-DAILY-001 em save_file.emulated.catalog.demo_profiles()."
        )
    return plans[0]
