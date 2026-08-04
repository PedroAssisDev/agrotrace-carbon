from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from model_training_service.data.dataset_builder import safe_slug
from model_training_service.domain.enums import VersionStatus
from model_training_service.registry.active_index import ActiveModelIndex


class ArtifactStore:
    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.root_dir / "registry.jsonl"
        self.active_index = ActiveModelIndex(self.root_dir)
        self._run_context: dict[str, Any] = {}

    def set_run_context(self, context: dict[str, Any]) -> None:
        self._run_context = dict(context)

    def save_regression(
        self,
        *,
        model: Any,
        granularity: str,
        target: str,
        selected_candidate: str,
        selected_params: dict[str, Any],
        metrics: dict[str, Any],
        candidate_results: list[dict[str, Any]],
        training_data: pd.DataFrame,
        feature: str,
        selection_comparison: dict[str, Any] | None = None,
        validation_strategy: str | None = None,
        feature_columns: list[str] | None = None,
        training_run_id: str | None = None,
        activate: bool = True,
    ) -> dict[str, Any]:
        manifest = build_dataset_manifest(training_data)
        version = build_version(manifest["sha256"])
        directory = (
            self.root_dir
            / "regression"
            / granularity
            / "global"
            / target
            / version
        )
        logical_key = f"regression|{granularity}|{target}|global"
        previous = self.active_index.get(logical_key)
        status = VersionStatus.ACTIVE.value if activate else VersionStatus.CANDIDATE.value
        metadata = {
            "model_id": f"regression-{granularity}-global-{target}-{version}",
            "version": version,
            "model_family": "regression",
            "model_scope": "global",
            "property_id": None,
            "granularity": granularity,
            "target": target,
            "feature_schema": [{"name": feature, "type": "number", "minimum": 0}],
            "feature_columns": feature_columns or [feature],
            "forecast_horizon": 1,
            "regression_contract": (
                "contemporaneous_applied_to_future_scenario"
            ),
            "selected_candidate": selected_candidate,
            "selected_params": selected_params,
            "selection_comparison": selection_comparison or {},
            "validation_strategy": validation_strategy,
            "status": status,
            "active": bool(activate),
            "training_run_id": training_run_id,
            "supersedes": (previous or {}).get("model_id"),
            "traceability": {
                "config_sha256": self._run_context.get("config_sha256"),
                "environment_path": self._run_context.get("environment_path"),
                "resolved_config_path": self._run_context.get("resolved_config_path"),
            },
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._write_bundle(
            directory=directory,
            model=model,
            metadata=metadata,
            metrics={"selected": metrics, "candidates": candidate_results},
            manifest=manifest,
            data=training_data,
            data_filename="training_data.csv",
        )
        self._append_registry(metadata, directory)
        if activate:
            self.active_index.set_active(
                logical_key,
                model_id=metadata["model_id"],
                version=version,
                artifact_dir=str(directory),
                training_run_id=training_run_id,
                supersedes=metadata.get("supersedes"),
                metadata=metadata,
            )
        return {**metadata, "artifact_dir": str(directory), "logical_key": logical_key}

    def save_time_series(
        self,
        *,
        model: Any,
        property_id: str,
        target: str,
        selected_candidate: str,
        metrics: dict[str, Any],
        candidate_results: list[dict[str, Any]],
        training_series: pd.DataFrame,
        validation_predictions: pd.DataFrame,
        horizon: int,
        selection_comparison: dict[str, Any] | None = None,
        validation_strategy: str | None = None,
        training_run_id: str | None = None,
        activate: bool = True,
    ) -> dict[str, Any]:
        manifest = build_dataset_manifest(training_series)
        version = build_version(manifest["sha256"])
        property_slug = safe_slug(property_id)
        directory = (
            self.root_dir
            / "time_series"
            / "monthly"
            / property_slug
            / target
            / version
        )
        logical_key = f"time_series|monthly|{property_id}|{target}"
        previous = self.active_index.get(logical_key)
        status = VersionStatus.ACTIVE.value if activate else VersionStatus.CANDIDATE.value
        metadata = {
            "model_id": f"time-series-monthly-{property_slug}-{target}-{version}",
            "version": version,
            "model_family": "time_series",
            "model_scope": "property",
            "property_id": property_id,
            "granularity": "monthly",
            "target": target,
            "feature_schema": [],
            "uses_exogenous_variables": False,
            "forecast_horizon": horizon,
            "selected_candidate": selected_candidate,
            "selection_comparison": selection_comparison or {},
            "validation_strategy": validation_strategy,
            "status": status,
            "active": bool(activate),
            "training_run_id": training_run_id,
            "supersedes": (previous or {}).get("model_id"),
            "traceability": {
                "config_sha256": self._run_context.get("config_sha256"),
                "environment_path": self._run_context.get("environment_path"),
                "resolved_config_path": self._run_context.get("resolved_config_path"),
            },
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._write_bundle(
            directory=directory,
            model=model,
            metadata=metadata,
            metrics={"selected": metrics, "candidates": candidate_results},
            manifest=manifest,
            data=training_series,
            data_filename="training_series.csv",
        )
        validation_predictions.to_csv(directory / "validation_predictions.csv", index=False)
        self._append_registry(metadata, directory)
        if activate:
            self.active_index.set_active(
                logical_key,
                model_id=metadata["model_id"],
                version=version,
                artifact_dir=str(directory),
                training_run_id=training_run_id,
                supersedes=metadata.get("supersedes"),
                metadata=metadata,
            )
        return {**metadata, "artifact_dir": str(directory), "logical_key": logical_key}

    def _write_bundle(
        self,
        *,
        directory: Path,
        model: Any,
        metadata: dict[str, Any],
        metrics: dict[str, Any],
        manifest: dict[str, Any],
        data: pd.DataFrame,
        data_filename: str,
    ) -> None:
        directory.mkdir(parents=True, exist_ok=False)
        joblib.dump(model, directory / "model.joblib")
        _write_json(directory / "metadata.json", metadata)
        _write_json(directory / "metrics.json", metrics)
        _write_json(directory / "dataset_manifest.json", manifest)
        data.to_csv(directory / data_filename, index=False)

    def _append_registry(self, metadata: dict[str, Any], directory: Path) -> None:
        entry = {**metadata, "artifact_dir": str(directory)}
        with self.registry_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, default=_json_default) + "\n")


def build_dataset_manifest(data: pd.DataFrame) -> dict[str, Any]:
    csv_bytes = data.to_csv(index=False).encode("utf-8")
    period_start = None
    period_end = None
    if "period" in data.columns and not data.empty:
        periods = pd.to_datetime(data["period"])
        period_start = periods.min().isoformat()
        period_end = periods.max().isoformat()
    return {
        "sha256": hashlib.sha256(csv_bytes).hexdigest(),
        "row_count": int(len(data)),
        "columns": list(data.columns),
        "property_count": int(data["property_id"].nunique()) if "property_id" in data else None,
        "period_start": period_start,
        "period_end": period_end,
    }


def build_version(dataset_hash: str) -> str:
    timestamp = datetime.now(UTC).strftime("v%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}-{dataset_hash[:8]}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, default=_json_default)


def _json_default(value: Any):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return str(value)
