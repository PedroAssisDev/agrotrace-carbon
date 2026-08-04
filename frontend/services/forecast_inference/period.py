"""Derivação do período previsto a partir do histórico/manifesto."""

from __future__ import annotations

from typing import Any

import pandas as pd


def next_period_label(
    *,
    granularity: str,
    history: pd.DataFrame | None,
    property_id: str | None,
    manifest: dict[str, Any] | None,
) -> str:
    last = _last_period(history, property_id) or _manifest_period_end(manifest)
    if last is None or pd.isna(last):
        return "Próximo período"
    ts = pd.Timestamp(last)
    if granularity == "annual":
        return str(ts.year + 1)
    nxt = (ts.to_period("M") + 1).to_timestamp()
    months = (
        "jan", "fev", "mar", "abr", "mai", "jun",
        "jul", "ago", "set", "out", "nov", "dez",
    )
    return f"{months[nxt.month - 1]}/{nxt.year}"


def next_periods_monthly(history: pd.DataFrame | None, horizon: int = 3) -> list[str]:
    last = _last_period(history, None)
    if last is None or pd.isna(last):
        return [f"M+{i}" for i in range(1, horizon + 1)]
    ts = pd.Timestamp(last).to_period("M")
    months = (
        "jan", "fev", "mar", "abr", "mai", "jun",
        "jul", "ago", "set", "out", "nov", "dez",
    )
    labels: list[str] = []
    for i in range(1, horizon + 1):
        nxt = (ts + i).to_timestamp()
        labels.append(f"{months[nxt.month - 1]}/{nxt.year}")
    return labels


def _last_period(history: pd.DataFrame | None, property_id: str | None) -> pd.Timestamp | None:
    if history is None or history.empty or "period" not in history.columns:
        return None
    data = history
    if property_id and "property_id" in data.columns:
        filtered = data[data["property_id"].astype(str) == str(property_id)]
        if filtered.empty:
            return None
        data = filtered
    periods = pd.to_datetime(data["period"], errors="coerce").dropna()
    if periods.empty:
        return None
    return periods.max()


def _manifest_period_end(manifest: dict[str, Any] | None) -> pd.Timestamp | None:
    if not manifest:
        return None
    raw = manifest.get("period_end")
    if not raw:
        return None
    ts = pd.to_datetime(raw, errors="coerce")
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts)
