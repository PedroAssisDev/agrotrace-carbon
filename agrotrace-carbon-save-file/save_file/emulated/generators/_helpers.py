"""Helpers compartilhados entre geradores."""

from __future__ import annotations

import random
from dataclasses import dataclass

from save_file.emulated.catalog import DataQuality, EmulatedFarmProfile, HerdScale
from save_file.emulated.rng import clamp_int, jitter, seasonal_factor


@dataclass
class HerdSnapshot:
    lactating: int
    dry: int
    heifers: int
    calves: int
    bulls: int
    pregnant_heifers: int
    heifers_raising: int
    suckling_f: int
    suckling_m: int
    male_raising: int
    male_fattening: int
    draft_bulls: int
    equines: int


def effective_lactating(profile: EmulatedFarmProfile) -> int:
    base = profile.base_lactating_cows
    if profile.herd_scale == "small":
        return max(8, int(base * 0.45))
    if profile.herd_scale == "large":
        return int(base * 1.75)
    return base


def herd_for_month(rng: random.Random, profile: EmulatedFarmProfile, month: int) -> HerdSnapshot:
    lactating = clamp_int(rng, effective_lactating(profile), 5, 120, 2)
    dry = clamp_int(rng, max(2, lactating // 6), 0, 20, 1)
    heifers = clamp_int(rng, max(6, lactating // 2), 2, 40, 2)
    calves = clamp_int(rng, max(4, heifers // 2), 1, 30, 2)
    bulls = 1 if lactating > 30 else 0
    ph = max(1, heifers // 3)
    hr = max(2, heifers - ph)
    return HerdSnapshot(
        lactating=lactating,
        dry=dry,
        heifers=heifers,
        calves=calves,
        bulls=bulls,
        pregnant_heifers=ph,
        heifers_raising=hr,
        suckling_f=max(1, calves // 3),
        suckling_m=max(0, calves // 4),
        male_raising=max(0, calves // 5),
        male_fattening=1 if month >= 8 else 0,
        draft_bulls=1 if month % 6 == 0 else 0,
        equines=month % 3,
    )


def milk_liters_monthly(
    rng: random.Random,
    profile: EmulatedFarmProfile,
    month: int,
    lactating: int,
    *,
    quality: DataQuality,
    alert_spike: bool = False,
) -> float:
    liters_per_cow = 420.0
    if profile.herd_scale == "small":
        liters_per_cow = 380.0
    elif profile.herd_scale == "large":
        liters_per_cow = 460.0
    base = lactating * liters_per_cow * seasonal_factor(month)
    value = jitter(rng, base, 0.08)
    if quality == "alert" and alert_spike:
        value *= 3.0
    if quality == "incomplete" and month % 4 == 0:
        value *= 0.35
    return round(max(500.0, value), 1)


def tag_count_for_scale(scale: HerdScale, rng: random.Random) -> int:
    if scale == "small":
        return rng.randint(15, 25)
    if scale == "large":
        return rng.randint(40, 80)
    return rng.randint(22, 35)


def intraday_tags(profile: EmulatedFarmProfile, rng: random.Random) -> list[str]:
    n = tag_count_for_scale(profile.herd_scale, rng)
    return [f"T{1000 + i}" for i in range(n)]
