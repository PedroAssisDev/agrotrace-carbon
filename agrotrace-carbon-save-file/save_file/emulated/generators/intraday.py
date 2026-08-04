"""Gerador CSV intradiário (intraday:v1)."""

from __future__ import annotations

import csv
from datetime import date
from io import StringIO

from save_file.emulated.catalog import EmulatedFarmProfile
from save_file.emulated.generators._helpers import intraday_tags
from save_file.emulated.rng import derive_rng, jitter


def render_intraday_csv(
    profile: EmulatedFarmProfile,
    *,
    day: date,
    global_seed: int,
) -> str:
    rng = derive_rng(global_seed, profile.property_id, day.isoformat(), "intraday")
    tags = intraday_tags(profile, rng)
    day_num = (day - date(day.year, 1, 1)).days
    buf = StringIO()
    writer = csv.writer(buf, delimiter=",")
    writer.writerow(["Date", "Tag", "Milk", "Weight"])
    for i, tag in enumerate(tags):
        milk = round(jitter(rng, 38.0 + (day_num % 9) * 1.5 + i * 0.8, 0.12), 1)
        weight = round(jitter(rng, 580.0 + (day_num % 11) * 2.5 + i * 4.0, 0.05), 1)
        writer.writerow([day.isoformat(), tag, milk, weight])
    return buf.getvalue()
