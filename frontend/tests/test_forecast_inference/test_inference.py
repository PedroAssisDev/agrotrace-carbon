"""Testes da camada forecast_inference."""

from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import numpy as np
import pytest

from services.forecast_inference.errors import (
    InvalidInputError,
    MetadataIncompatibleError,
    ModelNotFoundError,
    OutOfDomainPredictionError,
    RegistryEmptyError,
    RegistryNotFoundError,
)
from services.forecast_inference.facade import PredictionFacade
from services.forecast_inference.loader import ArtifactCache, ModelArtifactLoader
from services.forecast_inference.registry import ModelRegistryReader
from services.forecast_inference.regression import RegressionInferenceService
from tests.test_forecast_inference.conftest import (
    NegativeForecaster,
    StubForecaster,
    append_registry,
    make_regression_artifact,
    make_timeseries_artifact,
    write_json,
)


def test_registry_not_found(tmp_path: Path):
    reader = ModelRegistryReader(tmp_path / "missing.jsonl", artifacts_root=tmp_path)
    with pytest.raises(RegistryNotFoundError):
        reader.read_all()


def test_registry_ignores_invalid_lines_and_picks_latest(tmp_path: Path):
    make_regression_artifact(
        tmp_path,
        target="milk_production_liters",
        granularity="monthly",
        version="v1",
        coef=1.0,
    )
    make_regression_artifact(
        tmp_path,
        target="milk_production_liters",
        granularity="monthly",
        version="v2",
        coef=2.0,
    )
    registry = tmp_path / "registry.jsonl"
    with registry.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")
        handle.write(json.dumps({"foo": 1}) + "\n")

    reader = ModelRegistryReader(registry, artifacts_root=tmp_path)
    latest = reader.find_latest(
        model_family="regression",
        model_scope="global",
        granularity="monthly",
        target="milk_production_liters",
        property_id=None,
    )
    assert latest["version"] == "v2"


def test_registry_filters_family_target_granularity_property(tmp_path: Path):
    make_regression_artifact(
        tmp_path, target="milk_production_liters", granularity="monthly", version="v1"
    )
    make_regression_artifact(
        tmp_path, target="total_ghg_emissions_tco2e", granularity="annual", version="v1"
    )
    make_timeseries_artifact(
        tmp_path,
        target="milk_production_liters",
        property_id="property-001",
        version="v1",
    )
    reader = ModelRegistryReader(tmp_path / "registry.jsonl", artifacts_root=tmp_path)

    with pytest.raises(ModelNotFoundError):
        reader.find_latest(
            model_family="regression",
            granularity="annual",
            target="milk_production_liters",
            model_scope="global",
        )

    ts = reader.find_latest(
        model_family="time_series",
        granularity="monthly",
        target="milk_production_liters",
        model_scope="property",
        property_id="property-001",
        forecast_horizon=3,
    )
    assert ts["property_id"] == "property-001"

    with pytest.raises(ModelNotFoundError):
        reader.find_latest(
            model_family="time_series",
            granularity="monthly",
            target="milk_production_liters",
            model_scope="property",
            property_id="property-999",
            forecast_horizon=3,
        )


def test_missing_artifact_skipped(tmp_path: Path):
    append_registry(
        tmp_path,
        {
            "model_id": "ghost",
            "version": "v0",
            "model_family": "regression",
            "model_scope": "global",
            "granularity": "monthly",
            "target": "milk_production_liters",
            "artifact_dir": str(tmp_path / "does-not-exist"),
        },
    )
    reader = ModelRegistryReader(tmp_path / "registry.jsonl", artifacts_root=tmp_path)
    with pytest.raises(ModelNotFoundError):
        reader.find_latest(
            model_family="regression",
            granularity="monthly",
            target="milk_production_liters",
            model_scope="global",
        )


def test_metadata_incompatible_features(tmp_path: Path):
    entry = make_regression_artifact(
        tmp_path, target="milk_production_liters", granularity="monthly", version="v1"
    )
    meta_path = Path(entry["artifact_dir"]) / "metadata.json"
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    payload["feature_columns"] = ["lactating_cows", "extra"]
    write_json(meta_path, payload)

    loader = ModelArtifactLoader()
    with pytest.raises(MetadataIncompatibleError):
        loader.load(entry, expect_family="regression")


def test_timeseries_rejects_wrong_horizon_metadata(tmp_path: Path):
    entry = make_timeseries_artifact(
        tmp_path,
        target="milk_production_liters",
        property_id="property-001",
        version="v1",
        forecast_horizon=6,
    )
    # Ajusta metadata para horizon 6 (registry já tem 6 — find_latest com 3 falha)
    reader = ModelRegistryReader(tmp_path / "registry.jsonl", artifacts_root=tmp_path)
    with pytest.raises(ModelNotFoundError):
        reader.find_latest(
            model_family="time_series",
            granularity="monthly",
            target="milk_production_liters",
            model_scope="property",
            property_id="property-001",
            forecast_horizon=3,
        )
    # Se forçarmos load direto com metadata horizon != 3
    meta = json.loads((Path(entry["artifact_dir"]) / "metadata.json").read_text(encoding="utf-8"))
    assert meta["forecast_horizon"] == 6
    loader = ModelArtifactLoader()
    with pytest.raises(MetadataIncompatibleError):
        loader.load(entry, expect_family="time_series")


def test_regression_predict_only_lactating_cows(tmp_path: Path, monkeypatch):
    make_regression_artifact(
        tmp_path, target="milk_production_liters", granularity="monthly", version="v1", coef=10.0, intercept=0.0
    )
    make_regression_artifact(
        tmp_path,
        target="total_ghg_emissions_tco2e",
        granularity="monthly",
        version="v1",
        coef=0.5,
        intercept=0.0,
    )
    facade = PredictionFacade(artifacts_dir=tmp_path, registry_path=tmp_path / "registry.jsonl")

    captured = {}

    original_predict = facade.regression.loader.load

    def wrapped_load(entry, expect_family=None):
        artifact = original_predict(entry, expect_family=expect_family)
        real_predict = artifact.model.predict

        def spy(X):
            captured["X"] = np.asarray(X)
            return real_predict(X)

        artifact.model.predict = spy  # type: ignore[method-assign]
        return artifact

    monkeypatch.setattr(facade.regression.loader, "load", wrapped_load)

    result = facade.predict_regression_scenario("property-001", "monthly", 20)
    assert captured["X"].shape == (1, 1)
    assert float(captured["X"][0, 0]) == 20.0
    assert result["predicted_milk_production_liters"] is not None
    assert result["predicted_total_ghg_emissions_tco2e"] is not None


@pytest.mark.parametrize(
    "cows",
    [None, "", -1, 1.5, True, "abc"],
)
def test_regression_invalid_cows(tmp_path: Path, cows):
    make_regression_artifact(
        tmp_path, target="milk_production_liters", granularity="monthly", version="v1"
    )
    facade = PredictionFacade(artifacts_dir=tmp_path, registry_path=tmp_path / "registry.jsonl")
    with pytest.raises(InvalidInputError):
        facade.predict_regression_scenario("property-001", "monthly", cows)


def test_timeseries_returns_three_points(tmp_path: Path):
    make_timeseries_artifact(
        tmp_path,
        target="milk_production_liters",
        property_id="property-001",
        version="v1",
        values=[10.0, 20.0, 30.0],
    )
    make_timeseries_artifact(
        tmp_path,
        target="total_ghg_emissions_tco2e",
        property_id="property-001",
        version="v1",
        values=[1.0, 2.0, 3.0],
    )
    facade = PredictionFacade(artifacts_dir=tmp_path, registry_path=tmp_path / "registry.jsonl")
    result = facade.forecast_time_series("property-001")
    assert result["forecast_horizon"] == 3
    assert result["milk_predictions"] == [10.0, 20.0, 30.0]
    assert result["emission_predictions"] == [1.0, 2.0, 3.0]
    assert len(result["periods"]) == 3


def test_timeseries_property_without_model(tmp_path: Path):
    make_timeseries_artifact(
        tmp_path,
        target="milk_production_liters",
        property_id="property-001",
        version="v1",
    )
    facade = PredictionFacade(artifacts_dir=tmp_path, registry_path=tmp_path / "registry.jsonl")
    with pytest.raises(ModelNotFoundError):
        facade.forecast_time_series("property-xyz")


def test_one_target_ok_other_missing(tmp_path: Path):
    make_regression_artifact(
        tmp_path, target="milk_production_liters", granularity="monthly", version="v1"
    )
    facade = PredictionFacade(artifacts_dir=tmp_path, registry_path=tmp_path / "registry.jsonl")
    result = facade.predict_regression_scenario("property-001", "monthly", 10)
    assert result["predicted_milk_production_liters"] is not None
    assert result["predicted_total_ghg_emissions_tco2e"] is None
    assert result["warnings"]


def test_negative_prediction_is_domain_error(tmp_path: Path):
    make_timeseries_artifact(
        tmp_path,
        target="milk_production_liters",
        property_id="property-001",
        version="v1",
        forecaster=NegativeForecaster(),
    )
    make_timeseries_artifact(
        tmp_path,
        target="total_ghg_emissions_tco2e",
        property_id="property-001",
        version="v1",
        values=[1.0, 2.0, 3.0],
    )
    facade = PredictionFacade(artifacts_dir=tmp_path, registry_path=tmp_path / "registry.jsonl")
    result = facade.forecast_time_series("property-001")
    assert result["milk_predictions"] is None
    assert result["emission_predictions"] == [1.0, 2.0, 3.0]
    assert any("negativa" in w.lower() or "domínio" in w.lower() for w in result["warnings"])


def test_cache_hit_and_invalidation_by_mtime(tmp_path: Path):
    entry = make_regression_artifact(
        tmp_path, target="milk_production_liters", granularity="monthly", version="v1"
    )
    cache = ArtifactCache()
    loader = ModelArtifactLoader(cache=cache)
    first = loader.load(entry, expect_family="regression")
    second = loader.load(entry, expect_family="regression")
    assert first is second

    model_path = Path(entry["artifact_dir"]) / "model.joblib"
    time.sleep(0.05)
    # regrava para mudar mtime
    joblib.dump(first.model, model_path)
    third = loader.load(entry, expect_family="regression")
    assert third is not first


def test_availability_summary(tmp_path: Path):
    make_regression_artifact(
        tmp_path, target="milk_production_liters", granularity="monthly", version="v1"
    )
    make_timeseries_artifact(
        tmp_path,
        target="milk_production_liters",
        property_id="property-001",
        version="v1",
    )
    facade = PredictionFacade(artifacts_dir=tmp_path, registry_path=tmp_path / "registry.jsonl")
    summary = facade.get_model_availability("property-001")
    assert summary["registry_ok"] is True
    assert summary["has_any_regression"] is True
    assert summary["has_property_timeseries"] is True
    summary_other = facade.get_model_availability("other")
    assert summary_other["has_property_timeseries"] is False
