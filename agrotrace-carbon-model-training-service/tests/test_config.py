from pathlib import Path

import pandas as pd
import pytest

from model_training_service.config import (
    hash_config,
    load_config,
    resolve_paths_relative_to_config,
)


def _write_yaml(path: Path, processed: str, artifacts: str) -> None:
    path.write_text(
        f"""
paths:
  processed_data_dir: {processed}
  artifacts_dir: {artifacts}
validation:
  approved_values: [approved]
  published_values: [published]
  duplicate_policy: reject
  monthly_gap_policy: reject
selection:
  metric: mae
  minimum_improvement_over_baseline: 0.0
regression:
  enabled: true
  granularities: [monthly]
  targets: [milk_production_liters]
  feature: lactating_cows
  scope: global
  min_records: 8
  random_state: 42
  max_cv_splits: 3
  candidate_profile: core
time_series:
  enabled: false
  granularity: monthly
  targets: [milk_production_liters]
  min_records: 12
  forecast_horizon: 3
  max_validation_folds: 2
  minimum_train_size: 8
  seasonal_period: 12
  enable_seasonal_models_from: 24
  enable_lstm: false
  lstm_min_records: 36
""",
        encoding="utf-8",
    )


def test_load_config_reads_selection_metric_mae(tmp_path: Path):
    config_path = tmp_path / "training.yaml"
    _write_yaml(config_path, "data/processed", "artifacts")
    config = load_config(config_path)
    assert config["selection"]["metric"] == "mae"


def test_load_config_reads_selection_metric_rmse(tmp_path: Path):
    config_path = tmp_path / "training.yaml"
    _write_yaml(config_path, "data/processed", "artifacts")
    text = config_path.read_text(encoding="utf-8").replace("metric: mae", "metric: rmse")
    config_path.write_text(text, encoding="utf-8")
    config = load_config(config_path)
    assert config["selection"]["metric"] == "rmse"


def test_load_config_rejects_unknown_metric(tmp_path: Path):
    config_path = tmp_path / "training.yaml"
    _write_yaml(config_path, "data/processed", "artifacts")
    text = config_path.read_text(encoding="utf-8").replace("metric: mae", "metric: mape")
    config_path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="selection.metric"):
        load_config(config_path)


def test_relative_paths_resolve_against_yaml_directory(tmp_path: Path):
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    config_path = config_dir / "training.yaml"
    _write_yaml(config_path, "data/processed", "artifacts")
    config = load_config(config_path)
    assert Path(config["paths"]["processed_data_dir"]) == (config_dir / "data" / "processed").resolve()
    assert Path(config["paths"]["artifacts_dir"]) == (config_dir / "artifacts").resolve()


def test_absolute_paths_unchanged(tmp_path: Path):
    processed = (tmp_path / "abs_processed").resolve()
    artifacts = (tmp_path / "abs_artifacts").resolve()
    config_path = tmp_path / "training.yaml"
    # YAML needs forward-slash or escaped backslash; use as_posix for portability
    _write_yaml(config_path, processed.as_posix(), artifacts.as_posix())
    config = load_config(config_path)
    assert Path(config["paths"]["processed_data_dir"]) == processed
    assert Path(config["paths"]["artifacts_dir"]) == artifacts


def test_paths_resolve_when_called_from_other_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    project = tmp_path / "project"
    other = tmp_path / "other"
    project.mkdir()
    other.mkdir()
    config_path = project / "training.yaml"
    _write_yaml(config_path, "out/processed", "out/artifacts")
    monkeypatch.chdir(other)
    config = load_config(config_path)
    assert Path(config["paths"]["artifacts_dir"]) == (project / "out" / "artifacts").resolve()


def test_hash_config_stable_for_same_payload():
    config = {
        "paths": {"processed_data_dir": "/a", "artifacts_dir": "/b"},
        "selection": {"metric": "mae"},
    }
    assert hash_config(config) == hash_config(config)


def test_resolve_paths_helper_matches_load(tmp_path: Path):
    config_path = tmp_path / "training.yaml"
    raw = {
        "paths": {"processed_data_dir": "p", "artifacts_dir": "a"},
        "validation": {},
        "selection": {},
        "regression": {},
        "time_series": {},
    }
    resolved = resolve_paths_relative_to_config(raw, config_path)
    assert Path(resolved["paths"]["artifacts_dir"]) == (tmp_path / "a").resolve()


def test_minimum_improvement_zero_is_valid(tmp_path: Path):
    config_path = tmp_path / "training.yaml"
    _write_yaml(config_path, "data/processed", "artifacts")
    config = load_config(config_path)
    assert config["selection"]["minimum_improvement_over_baseline"] == 0.0


def test_minimum_improvement_positive_is_valid(tmp_path: Path):
    config_path = tmp_path / "training.yaml"
    _write_yaml(config_path, "data/processed", "artifacts")
    text = config_path.read_text(encoding="utf-8").replace(
        "minimum_improvement_over_baseline: 0.0",
        "minimum_improvement_over_baseline: 5.0",
    )
    config_path.write_text(text, encoding="utf-8")
    config = load_config(config_path)
    assert config["selection"]["minimum_improvement_over_baseline"] == 5.0


def test_minimum_improvement_negative_raises(tmp_path: Path):
    config_path = tmp_path / "training.yaml"
    _write_yaml(config_path, "data/processed", "artifacts")
    text = config_path.read_text(encoding="utf-8").replace(
        "minimum_improvement_over_baseline: 0.0",
        "minimum_improvement_over_baseline: -1.0",
    )
    config_path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="minimum_improvement_over_baseline"):
        load_config(config_path)


def test_minimum_improvement_invalid_type_raises(tmp_path: Path):
    config_path = tmp_path / "training.yaml"
    _write_yaml(config_path, "data/processed", "artifacts")
    text = config_path.read_text(encoding="utf-8").replace(
        "minimum_improvement_over_baseline: 0.0",
        "minimum_improvement_over_baseline: not-a-number",
    )
    config_path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="minimum_improvement_over_baseline"):
        load_config(config_path)
