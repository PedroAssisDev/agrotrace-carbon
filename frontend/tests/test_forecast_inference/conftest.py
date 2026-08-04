"""Fixtures mínimas para testes da camada forecast_inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class StubForecaster:
    def __init__(self, values: list[float] | None = None) -> None:
        self.values = values or [100.0, 110.0, 120.0]

    def forecast(self, horizon: int):
        return np.array(self.values[:horizon], dtype=float)


class NegativeForecaster:
    def forecast(self, horizon: int):
        return np.array([-1.0] * horizon, dtype=float)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_registry(artifacts_root: Path, entry: dict[str, Any]) -> Path:
    registry = artifacts_root / "registry.jsonl"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    with registry.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return registry


def make_regression_artifact(
    artifacts_root: Path,
    *,
    target: str,
    granularity: str,
    version: str,
    coef: float = 10.0,
    intercept: float = 5.0,
    property_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    artifact_dir = (
        artifacts_root / "regression" / granularity / "global" / target / version
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", LinearRegression()),
        ]
    )
    # Fit com relação determinística y = coef * x + intercept
    x = np.array([[1.0], [2.0], [3.0], [4.0]])
    y = coef * x.ravel() + intercept
    model.fit(x, y)
    joblib.dump(model, artifact_dir / "model.joblib")

    metadata = {
        "model_id": f"reg-{granularity}-{target}-{version}",
        "version": version,
        "model_family": "regression",
        "model_scope": "global",
        "granularity": granularity,
        "target": target,
        "feature_columns": ["lactating_cows"],
        "selected_candidate": "linear",
        "created_at": f"2024-01-01T00:00:00Z",
    }
    write_json(artifact_dir / "metadata.json", metadata)
    write_json(
        artifact_dir / "metrics.json",
        {"selected": {"rmse": 1.0, "mae": 0.5}},
    )
    write_json(
        artifact_dir / "dataset_manifest.json",
        {
            "row_count": 4,
            "period_start": "2023-01-01",
            "period_end": "2023-12-01",
        },
    )
    rows = property_rows or [
        {
            "property_id": "property-001",
            "period": "2023-10-01",
            "lactating_cows": 10,
            target: 100.0,
        },
        {
            "property_id": "property-001",
            "period": "2023-11-01",
            "lactating_cows": 12,
            target: 120.0,
        },
        {
            "property_id": "property-001",
            "period": "2023-12-01",
            "lactating_cows": 14,
            target: 140.0,
        },
    ]
    pd.DataFrame(rows).to_csv(artifact_dir / "training_data.csv", index=False)

    entry = {
        "model_id": metadata["model_id"],
        "version": version,
        "model_family": "regression",
        "model_scope": "global",
        "granularity": granularity,
        "target": target,
        "property_id": None,
        "artifact_dir": str(artifact_dir),
        "selected_candidate": "linear",
        "created_at": metadata["created_at"],
    }
    append_registry(artifacts_root, entry)
    return entry


def make_timeseries_artifact(
    artifacts_root: Path,
    *,
    target: str,
    property_id: str,
    version: str,
    values: list[float] | None = None,
    forecaster: Any | None = None,
    forecast_horizon: int = 3,
) -> dict[str, Any]:
    slug = property_id.replace(" ", "-")
    artifact_dir = (
        artifacts_root / "time_series" / "monthly" / slug / target / version
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model = forecaster or StubForecaster(values)
    joblib.dump(model, artifact_dir / "model.joblib")

    metadata = {
        "model_id": f"ts-{slug}-{target}-{version}",
        "version": version,
        "model_family": "time_series",
        "model_scope": "property",
        "granularity": "monthly",
        "target": target,
        "property_id": property_id,
        "forecast_horizon": forecast_horizon,
        "uses_exogenous_variables": False,
        "selected_candidate": "naive",
        "created_at": "2024-02-01T00:00:00Z",
    }
    write_json(artifact_dir / "metadata.json", metadata)
    write_json(
        artifact_dir / "metrics.json",
        {"selected": {"rmse": 2.0, "mae": 1.5}},
    )
    write_json(
        artifact_dir / "dataset_manifest.json",
        {
            "row_count": 12,
            "period_start": "2023-01-01",
            "period_end": "2023-12-01",
        },
    )
    series = pd.DataFrame(
        {
            "period": pd.date_range("2023-01-01", periods=12, freq="MS"),
            target: np.linspace(100, 200, 12),
        }
    )
    series.to_csv(artifact_dir / "training_series.csv", index=False)

    entry = {
        "model_id": metadata["model_id"],
        "version": version,
        "model_family": "time_series",
        "model_scope": "property",
        "granularity": "monthly",
        "target": target,
        "property_id": property_id,
        "forecast_horizon": forecast_horizon,
        "artifact_dir": str(artifact_dir),
        "selected_candidate": "naive",
        "created_at": metadata["created_at"],
    }
    append_registry(artifacts_root, entry)
    return entry
