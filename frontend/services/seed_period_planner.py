"""Planejamento de entradas de dados e grupos de aprovação para o seed."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Iterator


def build_entry_id(prefix: str, index: int, width: int = 3) -> str:
    return f"{prefix}-{index:0{width}d}"


def iter_months(year: int) -> Iterator[tuple[int, int]]:
    for month in range(1, 13):
        yield year, month


def iter_years(start: int, end: int) -> Iterator[int]:
    for year in range(start, end + 1):
        yield year


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


MONTH_LABELS_PT = (
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
)


def _month_label(year: int, month: int) -> str:
    return f"{MONTH_LABELS_PT[month - 1]}/{year}"


def plan_monthly_boa_vista() -> SeedScenarioPlan:
    scenario_key = "monthly_boa_vista"
    property_id = "FARM-MONTHLY-001"
    property_name = "Fazenda Boa Vista Leiteira"
    entry_prefix = "ANNUAL-2026-FARM-MONTHLY"
    year = 2026
    entries: list[SeedDataEntry] = []
    groups: list[SeedApprovalGroup] = []

    for idx, month in enumerate(range(1, 13), start=1):
        period_key = f"{year}-{month:02d}"
        entry = SeedDataEntry(
            entry_id=build_entry_id(entry_prefix, idx),
            scenario_key=scenario_key,
            property_id=property_id,
            property_name=property_name,
            data_granularity="monthly",
            period_key=period_key,
            reporting_period=period_key,
            approval_group_key=period_key,
            layout="monthly",
            index=idx,
            year=year,
            month=month,
        )
        entries.append(entry)
        groups.append(
            SeedApprovalGroup(
                cycle_id=entry.entry_id,
                scenario_key=scenario_key,
                property_id=property_id,
                property_name=property_name,
                reporting_period=period_key,
                approval_granularity="monthly",
                data_granularity="monthly",
                layout="monthly",
                approval_group_key=period_key,
                coverage_label=f"Mensal ({_month_label(year, month)})",
                entries=[entry],
                index=idx,
            )
        )

    return SeedScenarioPlan(
        scenario_key=scenario_key,
        property_id=property_id,
        property_name=property_name,
        data_granularity="monthly",
        approval_granularity="monthly",
        layout="monthly",
        entry_prefix=entry_prefix,
        entries=entries,
        approval_groups=groups,
    )


def plan_annual_santa_clara() -> SeedScenarioPlan:
    scenario_key = "annual_santa_clara"
    property_id = "FARM-ANNUAL-001"
    property_name = "Fazenda Santa Clara Sustentável"
    entry_prefix = "ANNUAL-2021-2025-FARM-ANNUAL"
    entries: list[SeedDataEntry] = []
    groups: list[SeedApprovalGroup] = []

    for idx, year in enumerate(iter_years(2021, 2025), start=1):
        period_key = str(year)
        entry = SeedDataEntry(
            entry_id=build_entry_id(entry_prefix, idx),
            scenario_key=scenario_key,
            property_id=property_id,
            property_name=property_name,
            data_granularity="annual",
            period_key=period_key,
            reporting_period=period_key,
            approval_group_key=period_key,
            layout="annual",
            index=idx,
            year=year,
        )
        entries.append(entry)
        groups.append(
            SeedApprovalGroup(
                cycle_id=entry.entry_id,
                scenario_key=scenario_key,
                property_id=property_id,
                property_name=property_name,
                reporting_period=period_key,
                approval_granularity="annual",
                data_granularity="annual",
                layout="annual",
                approval_group_key=period_key,
                coverage_label=f"Anual ({year})",
                entries=[entry],
                index=idx,
            )
        )

    return SeedScenarioPlan(
        scenario_key=scenario_key,
        property_id=property_id,
        property_name=property_name,
        data_granularity="annual",
        approval_granularity="annual",
        layout="annual",
        entry_prefix=entry_prefix,
        entries=entries,
        approval_groups=groups,
    )


def plan_daily_experimental() -> SeedScenarioPlan:
    scenario_key = "daily_experimental"
    property_id = "FARM-DAILY-001"
    property_name = "Fazenda Experimental Sensorial"
    entry_prefix = "DAILY-2026-01-2026-06-FARM-DAILY"
    approval_prefix = "MONTHLY-2026"
    start = date(2026, 1, 1)
    end = date(2026, 6, 30)
    day_list = list(iter_days(start, end))
    monthly_groups = group_daily_by_month(day_list)

    entries: list[SeedDataEntry] = []
    groups: list[SeedApprovalGroup] = []
    entry_idx = 0

    for group_idx, (month_key, days) in enumerate(sorted(monthly_groups.items()), start=1):
        group_entries: list[SeedDataEntry] = []
        year, month = int(month_key[:4]), int(month_key[5:7])
        cycle_id = build_entry_id(f"{approval_prefix}-{month:02d}-FARM-DAILY", group_idx)

        for d in days:
            entry_idx += 1
            period_key = d.isoformat()
            entry = SeedDataEntry(
                entry_id=build_entry_id(entry_prefix, entry_idx),
                scenario_key=scenario_key,
                property_id=property_id,
                property_name=property_name,
                data_granularity="daily",
                period_key=period_key,
                reporting_period=period_key,
                approval_group_key=month_key,
                layout="intraday",
                index=entry_idx,
                year=year,
                month=month,
                day=d,
            )
            entries.append(entry)
            group_entries.append(entry)

        groups.append(
            SeedApprovalGroup(
                cycle_id=cycle_id,
                scenario_key=scenario_key,
                property_id=property_id,
                property_name=property_name,
                reporting_period=month_key,
                approval_granularity="monthly",
                data_granularity="daily",
                layout="intraday",
                approval_group_key=month_key,
                coverage_label=(
                    f"Diário consolidado mensal ({_month_label(year, month)} — "
                    f"{len(group_entries)} dias)"
                ),
                entries=group_entries,
                index=group_idx,
            )
        )

    return SeedScenarioPlan(
        scenario_key=scenario_key,
        property_id=property_id,
        property_name=property_name,
        data_granularity="daily",
        approval_granularity="monthly",
        layout="intraday",
        entry_prefix=entry_prefix,
        entries=entries,
        approval_groups=groups,
    )


def build_all_seed_plans() -> list[SeedScenarioPlan]:
    return [
        plan_monthly_boa_vista(),
        plan_annual_santa_clara(),
        plan_daily_experimental(),
    ]


def all_data_entries(plans: list[SeedScenarioPlan] | None = None) -> list[SeedDataEntry]:
    plans = plans or build_all_seed_plans()
    return [entry for plan in plans for entry in plan.entries]


def all_approval_groups(plans: list[SeedScenarioPlan] | None = None) -> list[SeedApprovalGroup]:
    plans = plans or build_all_seed_plans()
    return [group for plan in plans for group in plan.approval_groups]


def expected_entry_count() -> int:
    return len(all_data_entries())


def expected_approval_count() -> int:
    return len(all_approval_groups())


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
