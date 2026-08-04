"""Catálogo de perfis de fazenda emulada."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

HerdScale = Literal["small", "medium", "large"]
DataQuality = Literal["complete", "incomplete", "alert"]


@dataclass(frozen=True)
class EmulatedScenario:
    """Cenário de geração para uma fazenda."""

    scenario_key: str
    data_granularity: Literal["monthly", "annual", "daily"]
    approval_granularity: Literal["monthly", "annual"]
    layout: Literal["monthly", "annual", "intraday"]
    entry_prefix: str
    # monthly: list of (year, month); annual: list of years; daily: (start, end)
    months: tuple[tuple[int, int], ...] = ()
    years: tuple[int, ...] = ()
    daily_start: date | None = None
    daily_end: date | None = None


@dataclass(frozen=True)
class EmulatedFarmProfile:
    property_id: str
    name: str
    municipality: str
    state: str
    production_type: str
    herd_scale: HerdScale
    area_ha: float
    base_lactating_cows: int
    data_quality: DataQuality
    scenarios: tuple[EmulatedScenario, ...] = field(default_factory=tuple)


def _scale_cows(scale: HerdScale, base: int) -> int:
    if scale == "small":
        return max(8, int(base * 0.45))
    if scale == "large":
        return int(base * 1.75)
    return base


def demo_profiles() -> list[EmulatedFarmProfile]:
    """Três fazendas do seed legado — 198 entradas / 23 ciclos."""
    return [
        EmulatedFarmProfile(
            property_id="FARM-MONTHLY-001",
            name="Fazenda Boa Vista Leiteira",
            municipality="Uberaba",
            state="MG",
            production_type="leite",
            herd_scale="medium",
            area_ha=145.0,
            base_lactating_cows=22,
            data_quality="complete",
            scenarios=(
                EmulatedScenario(
                    scenario_key="monthly_boa_vista",
                    data_granularity="monthly",
                    approval_granularity="monthly",
                    layout="monthly",
                    entry_prefix="ANNUAL-2026-FARM-MONTHLY",
                    months=tuple((2026, m) for m in range(1, 13)),
                ),
            ),
        ),
        EmulatedFarmProfile(
            property_id="FARM-ANNUAL-001",
            name="Fazenda Santa Clara Sustentável",
            municipality="Patos de Minas",
            state="MG",
            production_type="leite",
            herd_scale="large",
            area_ha=280.0,
            base_lactating_cows=26,
            data_quality="complete",
            scenarios=(
                EmulatedScenario(
                    scenario_key="annual_santa_clara",
                    data_granularity="annual",
                    approval_granularity="annual",
                    layout="annual",
                    entry_prefix="ANNUAL-2021-2025-FARM-ANNUAL",
                    years=(2021, 2022, 2023, 2024, 2025),
                ),
            ),
        ),
        EmulatedFarmProfile(
            property_id="FARM-DAILY-001",
            name="Fazenda Experimental Sensorial",
            municipality="Rio Verde",
            state="GO",
            production_type="leite",
            herd_scale="medium",
            area_ha=95.0,
            base_lactating_cows=20,
            data_quality="complete",
            scenarios=(
                EmulatedScenario(
                    scenario_key="daily_experimental",
                    data_granularity="daily",
                    approval_granularity="monthly",
                    layout="intraday",
                    entry_prefix="DAILY-2026-01-2026-06-FARM-DAILY",
                    daily_start=date(2026, 1, 1),
                    daily_end=date(2026, 6, 30),
                ),
            ),
        ),
    ]


def full_profiles() -> list[EmulatedFarmProfile]:
    """Perfis demo + fazendas extras para testes de qualidade/porte."""
    extra = [
        EmulatedFarmProfile(
            property_id="FARM-SMALL-001",
            name="Sítio Bela Vista",
            municipality="Lambari",
            state="MG",
            production_type="leite",
            herd_scale="small",
            area_ha=42.0,
            base_lactating_cows=12,
            data_quality="complete",
            scenarios=(
                EmulatedScenario(
                    scenario_key="monthly_small",
                    data_granularity="monthly",
                    approval_granularity="monthly",
                    layout="monthly",
                    entry_prefix="SMALL-2026-FARM-SMALL",
                    months=tuple((2026, m) for m in range(1, 7)),
                ),
            ),
        ),
        EmulatedFarmProfile(
            property_id="FARM-LARGE-001",
            name="Fazenda Horizonte Leite",
            municipality="Passos",
            state="MG",
            production_type="leite",
            herd_scale="large",
            area_ha=520.0,
            base_lactating_cows=48,
            data_quality="complete",
            scenarios=(
                EmulatedScenario(
                    scenario_key="monthly_large",
                    data_granularity="monthly",
                    approval_granularity="monthly",
                    layout="monthly",
                    entry_prefix="LARGE-2026-FARM-LARGE",
                    months=tuple((2026, m) for m in range(1, 13)),
                ),
            ),
        ),
        EmulatedFarmProfile(
            property_id="FARM-INCOMPLETE-001",
            name="Fazenda Dados Parciais",
            municipality="Araxá",
            state="MG",
            production_type="leite",
            herd_scale="small",
            area_ha=55.0,
            base_lactating_cows=14,
            data_quality="incomplete",
            scenarios=(
                EmulatedScenario(
                    scenario_key="annual_incomplete",
                    data_granularity="annual",
                    approval_granularity="annual",
                    layout="annual",
                    entry_prefix="INCOMPLETE-FARM-INCOMPLETE",
                    years=(2024, 2025),
                ),
            ),
        ),
        EmulatedFarmProfile(
            property_id="FARM-QUALITY-001",
            name="Fazenda Alerta Qualidade",
            municipality="Franca",
            state="SP",
            production_type="leite",
            herd_scale="medium",
            area_ha=110.0,
            base_lactating_cows=18,
            data_quality="alert",
            scenarios=(
                EmulatedScenario(
                    scenario_key="monthly_quality",
                    data_granularity="monthly",
                    approval_granularity="monthly",
                    layout="monthly",
                    entry_prefix="QUALITY-2026-FARM-QUALITY",
                    months=((2026, 1), (2026, 2), (2026, 3)),
                ),
            ),
        ),
    ]
    return demo_profiles() + extra


def get_profiles(mode: str = "demo") -> list[EmulatedFarmProfile]:
    if mode == "full":
        return full_profiles()
    return demo_profiles()
