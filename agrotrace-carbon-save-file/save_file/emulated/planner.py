"""Planejamento de entradas e grupos de aprovação para dados emulados."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterator

from save_file.emulated.catalog import EmulatedFarmProfile, EmulatedScenario, get_profiles

MONTH_LABELS_PT = (
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
)


def build_entry_id(prefix: str, index: int, width: int = 3) -> str:
    return f"{prefix}-{index:0{width}d}"


def iter_days(start: date, end: date) -> Iterator[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def group_daily_by_month(days: list[date]) -> dict[str, list[date]]:
    groups: dict[str, list[date]] = {}
    for d in days:
        key = f"{d.year}-{d.month:02d}"
        groups.setdefault(key, []).append(d)
    return groups


def _month_label(year: int, month: int) -> str:
    return f"{MONTH_LABELS_PT[month - 1]}/{year}"


@dataclass(frozen=True)
class PlannedEntry:
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
    alert_spike: bool = False


@dataclass
class PlannedApprovalGroup:
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
    entries: list[PlannedEntry] = field(default_factory=list)
    index: int = 1


def _plan_scenario(profile: EmulatedFarmProfile, scenario: EmulatedScenario) -> tuple[list[PlannedEntry], list[PlannedApprovalGroup]]:
    entries: list[PlannedEntry] = []
    groups: list[PlannedApprovalGroup] = []

    if scenario.data_granularity == "monthly":
        for idx, (year, month) in enumerate(scenario.months, start=1):
            period_key = f"{year}-{month:02d}"
            alert = profile.data_quality == "alert" and month == 2
            entry = PlannedEntry(
                entry_id=build_entry_id(scenario.entry_prefix, idx),
                scenario_key=scenario.scenario_key,
                property_id=profile.property_id,
                property_name=profile.name,
                data_granularity="monthly",
                period_key=period_key,
                reporting_period=period_key,
                approval_group_key=period_key,
                layout=scenario.layout,
                index=idx,
                year=year,
                month=month,
                alert_spike=alert,
            )
            entries.append(entry)
            groups.append(
                PlannedApprovalGroup(
                    cycle_id=entry.entry_id,
                    scenario_key=scenario.scenario_key,
                    property_id=profile.property_id,
                    property_name=profile.name,
                    reporting_period=period_key,
                    approval_granularity="monthly",
                    data_granularity="monthly",
                    layout=scenario.layout,
                    approval_group_key=period_key,
                    coverage_label=f"Mensal ({_month_label(year, month)})",
                    entries=[entry],
                    index=idx,
                )
            )
        return entries, groups

    if scenario.data_granularity == "annual":
        for idx, year in enumerate(scenario.years, start=1):
            period_key = str(year)
            entry = PlannedEntry(
                entry_id=build_entry_id(scenario.entry_prefix, idx),
                scenario_key=scenario.scenario_key,
                property_id=profile.property_id,
                property_name=profile.name,
                data_granularity="annual",
                period_key=period_key,
                reporting_period=period_key,
                approval_group_key=period_key,
                layout=scenario.layout,
                index=idx,
                year=year,
            )
            entries.append(entry)
            groups.append(
                PlannedApprovalGroup(
                    cycle_id=entry.entry_id,
                    scenario_key=scenario.scenario_key,
                    property_id=profile.property_id,
                    property_name=profile.name,
                    reporting_period=period_key,
                    approval_granularity="annual",
                    data_granularity="annual",
                    layout=scenario.layout,
                    approval_group_key=period_key,
                    coverage_label=f"Anual ({year})",
                    entries=[entry],
                    index=idx,
                )
            )
        return entries, groups

    if scenario.data_granularity == "daily":
        assert scenario.daily_start and scenario.daily_end
        day_list = list(iter_days(scenario.daily_start, scenario.daily_end))
        monthly_groups = group_daily_by_month(day_list)
        approval_prefix = "MONTHLY-2026"
        entry_idx = 0
        for group_idx, (month_key, days) in enumerate(sorted(monthly_groups.items()), start=1):
            group_entries: list[PlannedEntry] = []
            year, month = int(month_key[:4]), int(month_key[5:7])
            cycle_id = build_entry_id(f"{approval_prefix}-{month:02d}-FARM-DAILY", group_idx)
            for d in days:
                entry_idx += 1
                period_key = d.isoformat()
                entry = PlannedEntry(
                    entry_id=build_entry_id(scenario.entry_prefix, entry_idx),
                    scenario_key=scenario.scenario_key,
                    property_id=profile.property_id,
                    property_name=profile.name,
                    data_granularity="daily",
                    period_key=period_key,
                    reporting_period=period_key,
                    approval_group_key=month_key,
                    layout=scenario.layout,
                    index=entry_idx,
                    year=year,
                    month=month,
                    day=d,
                )
                entries.append(entry)
                group_entries.append(entry)
            groups.append(
                PlannedApprovalGroup(
                    cycle_id=cycle_id,
                    scenario_key=scenario.scenario_key,
                    property_id=profile.property_id,
                    property_name=profile.name,
                    reporting_period=month_key,
                    approval_granularity="monthly",
                    data_granularity="daily",
                    layout=scenario.layout,
                    approval_group_key=month_key,
                    coverage_label=(
                        f"Diário consolidado mensal ({_month_label(year, month)} — "
                        f"{len(group_entries)} dias)"
                    ),
                    entries=group_entries,
                    index=group_idx,
                )
            )
        return entries, groups

    raise ValueError(f"Granularidade desconhecida: {scenario.data_granularity}")


def plan_all(profile_mode: str = "demo") -> tuple[list[EmulatedFarmProfile], list[PlannedEntry], list[PlannedApprovalGroup]]:
    profiles = get_profiles(profile_mode)
    all_entries: list[PlannedEntry] = []
    all_groups: list[PlannedApprovalGroup] = []
    for profile in profiles:
        for scenario in profile.scenarios:
            entries, groups = _plan_scenario(profile, scenario)
            all_entries.extend(entries)
            all_groups.extend(groups)
    return profiles, all_entries, all_groups


def expected_entry_count(profile_mode: str = "demo") -> int:
    _, entries, _ = plan_all(profile_mode)
    return len(entries)


def expected_approval_count(profile_mode: str = "demo") -> int:
    _, _, groups = plan_all(profile_mode)
    return len(groups)
