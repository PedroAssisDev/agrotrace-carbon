"""Histórico observado da propriedade a partir da fonte canônica de treino."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from services.forecast_inference.period import next_period_label
from services.training_data_export_service import approved_results_export_path


def training_results_csv_path() -> Path:
    return Path(approved_results_export_path())


def load_property_history_frame(
    property_id: str,
    granularity: str,
    *,
    csv_path: Path | None = None,
) -> pd.DataFrame:
    """Carrega histórico mensal/anual da propriedade no CSV de treino."""
    path = Path(csv_path or training_results_csv_path())
    if not path.exists() or not property_id:
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    if frame.empty or "property_id" not in frame.columns:
        return pd.DataFrame()
    subset = frame[
        frame["property_id"].astype(str).eq(str(property_id))
        & frame["granularity"].astype(str).eq(str(granularity))
    ].copy()
    if subset.empty or "period" not in subset.columns:
        return pd.DataFrame()
    subset["period"] = pd.to_datetime(subset["period"], errors="coerce")
    subset = subset.dropna(subset=["period"]).sort_values("period")
    return subset.reset_index(drop=True)


def history_rows_for_property(
    property_id: str,
    granularity: str,
    *,
    csv_path: Path | None = None,
) -> list[dict[str, Any]]:
    frame = load_property_history_frame(property_id, granularity, csv_path=csv_path)
    if frame.empty:
        return []
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        item: dict[str, Any] = {
            "period": pd.Timestamp(row["period"]).isoformat(),
            "lactating_cows": _optional_float(row.get("lactating_cows")),
            "milk_production_liters": _optional_float(row.get("milk_production_liters")),
            "total_ghg_emissions_tco2e": _optional_float(row.get("total_ghg_emissions_tco2e")),
        }
        rows.append(item)
    return rows


def get_regression_scenario_defaults(
    property_id: str,
    granularity: str = "monthly",
    *,
    csv_path: Path | None = None,
) -> dict[str, Any]:
    """Último período observado, vacas e rótulo do período seguinte."""
    frame = load_property_history_frame(property_id, granularity, csv_path=csv_path)
    if frame.empty:
        return {
            "property_id": property_id,
            "granularity": granularity,
            "last_period": None,
            "last_period_label": None,
            "last_lactating_cows": None,
            "forecast_period": "Próximo período",
            "record_count": 0,
        }

    last = frame.iloc[-1]
    last_ts = pd.Timestamp(last["period"])
    months = (
        "jan", "fev", "mar", "abr", "mai", "jun",
        "jul", "ago", "set", "out", "nov", "dez",
    )
    if granularity == "annual":
        last_label = str(last_ts.year)
    else:
        last_label = f"{months[last_ts.month - 1]}/{last_ts.year}"

    forecast_period = next_period_label(
        granularity=granularity,
        history=frame,
        property_id=property_id,
        manifest=None,
    )
    return {
        "property_id": property_id,
        "granularity": granularity,
        "last_period": last_ts.isoformat(),
        "last_period_label": last_label,
        "last_lactating_cows": _optional_int(last.get("lactating_cows")),
        "forecast_period": forecast_period,
        "record_count": int(len(frame)),
        "source_path": str(Path(csv_path or training_results_csv_path()).resolve()),
    }


def _optional_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(number):
        return None
    return number


def _optional_int(value: Any) -> int | None:
    number = _optional_float(value)
    if number is None:
        return None
    return int(round(number))
