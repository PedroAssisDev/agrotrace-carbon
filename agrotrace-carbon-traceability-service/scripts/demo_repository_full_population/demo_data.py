"""Fictional datasets for demo scenarios."""

from __future__ import annotations

from decimal import Decimal

from demo_config import FARM_BOA_VISTA, FARM_SANTA_CLARA, FARM_SAO_PEDRO, YEAR

# Case 1 — Fazenda São Pedro (annual direct)
SAO_PEDRO_ANNUAL = {
    "farm": FARM_SAO_PEDRO,
    "year": YEAR,
    "milk_liters": Decimal("144000"),
    "energy_kwh": Decimal("18500"),
    "lactating_cows_avg": Decimal("42"),
    "area_ha": Decimal("35"),
    "granularity": "annual",
}

# Case 2 — Fazenda Boa Vista (monthly → annual)
BOA_VISTA_MONTHLY_MILK_LITERS: dict[int, Decimal] = {
    1: Decimal("12000"),
    2: Decimal("11500"),
    3: Decimal("12300"),
    4: Decimal("12100"),
    5: Decimal("12600"),
    6: Decimal("11900"),
    7: Decimal("12800"),
    8: Decimal("13000"),
    9: Decimal("12700"),
    10: Decimal("13200"),
    11: Decimal("12900"),
    12: Decimal("13500"),
}
BOA_VISTA_ANNUAL_TOTAL = sum(BOA_VISTA_MONTHLY_MILK_LITERS.values())  # 150500

# Case 3 — Fazenda Santa Clara (daily January → monthly → annual)
SANTA_CLARA_DAILY_MILK_LITERS = Decimal("400")  # ~400 L/day in January
SANTA_CLARA_JANUARY_DAYS = 31
SANTA_CLARA_JANUARY_TOTAL = SANTA_CLARA_DAILY_MILK_LITERS * SANTA_CLARA_JANUARY_DAYS  # 12400

# Representative monthly totals Feb–Dec (simplified for demo scale)
SANTA_CLARA_OTHER_MONTHLY: dict[int, Decimal] = {
    m: Decimal("11000") + Decimal(m * 100) for m in range(2, 13)
}

# Case 4 — revision (Boa Vista January)
REVISION_JANUARY_V1 = Decimal("10000")
REVISION_JANUARY_V2 = Decimal("12000")
