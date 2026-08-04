from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("configs/training.yaml")

ALLOWED_SELECTION_METRICS = frozenset({"mae", "rmse"})
ALLOWED_GAP_POLICIES = frozenset({"reject", "skip_property"})
ALLOWED_CANDIDATE_PROFILES = frozenset({"core", "extended"})
ALLOWED_DUPLICATE_POLICIES = frozenset({"reject", "keep_last"})


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path or DEFAULT_CONFIG_PATH).resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    _validate_config(config)
    resolved = resolve_paths_relative_to_config(config, config_path)
    resolved["_meta"] = {
        "config_path": str(config_path),
        "config_sha256": hash_config(resolved),
    }
    return resolved


def resolve_paths_relative_to_config(
    config: dict[str, Any], config_path: str | Path
) -> dict[str, Any]:
    """Resolve paths.processed_data_dir and paths.artifacts_dir relative to the YAML file."""
    base = Path(config_path).resolve().parent
    resolved = copy.deepcopy(config)
    paths = resolved.setdefault("paths", {})
    for key in ("processed_data_dir", "artifacts_dir"):
        value = paths.get(key)
        if value is None:
            continue
        path = Path(value)
        if not path.is_absolute():
            path = (base / path).resolve()
        paths[key] = str(path)
    data_source = resolved.get("data_source")
    if isinstance(data_source, dict):
        for key in ("path", "location", "query_file", "sparql_query"):
            value = data_source.get(key)
            if not value:
                continue
            path = Path(str(value))
            if not path.is_absolute():
                data_source[key] = str((base / path).resolve())
    return resolved


def hash_config(config: dict[str, Any]) -> str:
    """SHA-256 of the effective config (paths resolved; internal _meta excluded)."""
    payload = {key: value for key, value in config.items() if key != "_meta"}
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_config(config: dict[str, Any]) -> None:
    required_sections = {"paths", "validation", "selection", "regression", "time_series"}
    missing = required_sections - set(config)
    if missing:
        raise ValueError(f"Seções ausentes na configuração: {sorted(missing)}")

    feature = config["regression"].get("feature")
    if feature != "lactating_cows":
        raise ValueError("A regressão deve usar exclusivamente a feature 'lactating_cows'.")

    profile = config["regression"].get("candidate_profile", "core")
    if profile not in ALLOWED_CANDIDATE_PROFILES:
        raise ValueError(f"candidate_profile inválido: {profile}. Use core ou extended.")

    if "selection_metric" in config["regression"]:
        raise ValueError(
            "regression.selection_metric foi removido; use selection.metric (mae|rmse)."
        )

    selection = config["selection"]
    metric = str(selection.get("metric", "mae")).lower()
    if metric not in ALLOWED_SELECTION_METRICS:
        raise ValueError(f"selection.metric inválida: {metric}. Use mae ou rmse.")
    selection["metric"] = metric
    try:
        minimum_improvement = float(
            selection.get("minimum_improvement_over_baseline", 0.0)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "minimum_improvement_over_baseline deve ser numérico e >= 0."
        ) from exc
    if minimum_improvement < 0:
        raise ValueError(
            "minimum_improvement_over_baseline deve ser >= 0; "
            f"valor recebido: {minimum_improvement}."
        )
    selection["minimum_improvement_over_baseline"] = minimum_improvement

    validation = config["validation"]
    gap_policy = str(validation.get("monthly_gap_policy", "reject")).lower()
    if gap_policy not in ALLOWED_GAP_POLICIES:
        raise ValueError(
            f"monthly_gap_policy inválida: {gap_policy}. Use reject ou skip_property."
        )
    validation["monthly_gap_policy"] = gap_policy

    duplicate_policy = str(validation.get("duplicate_policy", "reject")).lower()
    if duplicate_policy not in ALLOWED_DUPLICATE_POLICIES:
        raise ValueError(f"duplicate_policy inválida: {duplicate_policy}.")
    validation["duplicate_policy"] = duplicate_policy

    ts = config["time_series"]
    if ts.get("granularity") != "monthly":
        raise ValueError("A série temporal desta versão deve usar granularidade mensal.")

    if int(ts.get("forecast_horizon", 0)) != 3:
        raise ValueError("O horizonte da série temporal deve ser de três meses.")

    if "enable_lstm" not in ts:
        ts["enable_lstm"] = False
    else:
        ts["enable_lstm"] = bool(ts["enable_lstm"])
    if "lstm_min_records" not in ts:
        ts["lstm_min_records"] = 36
    else:
        ts["lstm_min_records"] = int(ts["lstm_min_records"])

    for key in ("processed_data_dir", "artifacts_dir"):
        if key not in config["paths"]:
            raise ValueError(f"paths.{key} é obrigatório.")
