from __future__ import annotations

import json
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Any

from model_training_service.config import hash_config


def _package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _git_info() -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
        return {
            "commit": commit or None,
            "working_tree_clean": status.strip() == "",
        }
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "working_tree_clean": None}


def build_training_environment(config: dict[str, Any]) -> dict[str, Any]:
    meta = config.get("_meta") or {}
    selection = config.get("selection") or {}
    validation = config.get("validation") or {}
    regression = config.get("regression") or {}
    time_series = config.get("time_series") or {}
    git = _git_info()
    config_sha = meta.get("config_sha256") or hash_config(config)
    return {
        "config_path": meta.get("config_path"),
        "config_sha256": config_sha,
        "random_state": regression.get("random_state"),
        "selection": {
            "metric": selection.get("metric"),
            "minimum_improvement_over_baseline": selection.get(
                "minimum_improvement_over_baseline"
            ),
            "regression_baseline": "mean_per_cow_baseline",
            "time_series_baseline": "naive",
        },
        "validation": {
            "monthly_gap_policy": validation.get("monthly_gap_policy"),
            "duplicate_policy": validation.get("duplicate_policy"),
        },
        "python_version": sys.version,
        "package_versions": {
            "pandas": _package_version("pandas"),
            "numpy": _package_version("numpy"),
            "scikit-learn": _package_version("scikit-learn"),
            "statsmodels": _package_version("statsmodels"),
            "joblib": _package_version("joblib"),
        },
        "git_commit": git["commit"],
        "git_working_tree_clean": git["working_tree_clean"],
        "time_series": {
            "forecast_horizon": time_series.get("forecast_horizon"),
            "enable_lstm": time_series.get("enable_lstm"),
            "lstm_min_records": time_series.get("lstm_min_records"),
        },
    }


def write_run_artifacts(artifacts_dir: str | Path, config: dict[str, Any]) -> dict[str, str]:
    root = Path(artifacts_dir)
    root.mkdir(parents=True, exist_ok=True)
    resolved = {key: value for key, value in config.items() if key != "_meta"}
    if "_meta" in config:
        resolved["_meta"] = {
            "config_path": config["_meta"].get("config_path"),
            "config_sha256": config["_meta"].get("config_sha256"),
        }
    environment = build_training_environment(config)
    resolved_path = root / "resolved_config.json"
    environment_path = root / "training_environment.json"
    resolved_path.write_text(
        json.dumps(resolved, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    environment_path.write_text(
        json.dumps(environment, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return {
        "resolved_config_path": str(resolved_path),
        "environment_path": str(environment_path),
    }
