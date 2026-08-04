"""Testes da fachada programatica de treinamento."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from model_training_service.api.contracts import ModelSlot, TrainModelsRequest
from model_training_service.api.facade import ModelTrainingFacade
from model_training_service.config import load_config
from model_training_service.domain.enums import TrainingMode
from model_training_service.domain.errors import (
    InvalidTrainingRequestError,
    TrainingConflictError,
)


@pytest.fixture()
def tiny_csv(tmp_path: Path) -> Path:
    rows = []
    # 3 properties x 12 months + annual
    for prop in ("property-001", "property-002", "property-003"):
        for month in range(1, 13):
            rows.append(
                {
                    "property_id": prop,
                    "period": f"2023-{month:02d}-01",
                    "granularity": "monthly",
                    "lactating_cows": 50 + month,
                    "milk_production_liters": 1000 + month * 10,
                    "total_ghg_emissions_tco2e": 10 + month * 0.1,
                    "approval_status": "approved",
                    "publication_status": "published",
                }
            )
        rows.append(
            {
                "property_id": prop,
                "period": "2023-01-01",
                "granularity": "annual",
                "lactating_cows": 60,
                "milk_production_liters": 12000,
                "total_ghg_emissions_tco2e": 120,
                "approval_status": "approved",
                "publication_status": "published",
            }
        )
        for year in range(2016, 2023):
            rows.append(
                {
                    "property_id": prop,
                    "period": f"{year}-01-01",
                    "granularity": "annual",
                    "lactating_cows": 55 + (year % 5),
                    "milk_production_liters": 11000 + year,
                    "total_ghg_emissions_tco2e": 100 + (year % 7),
                    "approval_status": "approved",
                    "publication_status": "published",
                }
            )
    # property with insufficient TS
    rows.append(
        {
            "property_id": "property-short",
            "period": "2023-01-01",
            "granularity": "monthly",
            "lactating_cows": 10,
            "milk_production_liters": 100,
            "total_ghg_emissions_tco2e": 1,
            "approval_status": "approved",
            "publication_status": "published",
        }
    )
    path = tmp_path / "data.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


@pytest.fixture()
def facade(tmp_path: Path, tiny_csv: Path) -> ModelTrainingFacade:
    base = Path(__file__).resolve().parents[1]
    cfg = load_config(base / "configs" / "training.yaml")
    cfg["paths"]["artifacts_dir"] = str(tmp_path / "artifacts")
    cfg["paths"]["processed_data_dir"] = str(tmp_path / "processed")
    cfg["data_source"] = {"type": "csv", "path": str(tiny_csv)}
    cfg["_meta"] = {"config_path": str(base / "configs" / "training.yaml"), "config_sha256": "test"}
    return ModelTrainingFacade(config=cfg, background=False)


def test_availability_six_slots(facade: ModelTrainingFacade):
    report = facade.get_model_availability("property-001")
    assert report.source_ok
    assert len(report.models) == 6
    monthly_reg = [m for m in report.models if m.family == "regression" and m.granularity == "monthly"]
    assert all(m.eligible for m in monthly_reg)
    ts = [m for m in report.models if m.family == "time_series"]
    assert all(m.eligible for m in ts)


def test_regression_global_for_multiple_properties(facade: ModelTrainingFacade):
    a = facade.get_model_availability("property-001")
    b = facade.get_model_availability("property-002")
    reg_a = [m for m in a.models if m.family == "regression"]
    reg_b = [m for m in b.models if m.family == "regression"]
    assert all(m.scope == "global" for m in reg_a)
    assert [m.target for m in reg_a] == [m.target for m in reg_b]


def test_ts_specific_and_ineligible_short(facade: ModelTrainingFacade):
    ok = facade.get_model_availability("property-001")
    short = facade.get_model_availability("property-short")
    assert any(m.family == "time_series" and m.eligible for m in ok.models)
    assert all(
        m.status == "ineligible"
        for m in short.models
        if m.family == "time_series"
    )


def test_ensure_missing_creates_versions(facade: ModelTrainingFacade, tmp_path: Path):
    report_before = facade.get_model_availability("property-001")
    assert all(m.status == "missing" for m in report_before.models if m.eligible)
    run = facade.ensure_models("property-001")
    assert run.status in {"completed", "partial"}
    assert run.models_created
    report_after = facade.get_model_availability("property-001")
    assert any(m.status == "available" for m in report_after.models)
    # versions not overwritten: directories exist under artifacts
    arts = Path(facade.config["paths"]["artifacts_dir"])
    assert (arts / "registry.jsonl").exists()
    assert (arts / "active_models.json").exists()


def test_retrain_creates_new_version_preserves_old(facade: ModelTrainingFacade):
    facade.ensure_models("property-001")
    before = facade.get_model_availability("property-001")
    milk = next(m for m in before.models if m.target.startswith("milk") and m.family == "regression" and m.granularity == "monthly")
    old_version = milk.active_version
    old_dir = Path(milk.artifact_dir)
    assert old_dir.is_dir()

    slot = ModelSlot(
        family="regression",
        scope="global",
        granularity="monthly",
        target="milk_production_liters",
    )
    run = facade.train_models(
        TrainModelsRequest(
            property_id="property-001",
            mode=TrainingMode.RETRAIN_SELECTED.value,
            slots=[slot],
        )
    )
    assert run.status in {"completed", "partial"}
    assert old_dir.is_dir()  # preserved
    after = facade.get_model_availability("property-001")
    milk2 = next(m for m in after.models if m.target.startswith("milk") and m.family == "regression" and m.granularity == "monthly")
    assert milk2.active_version != old_version


def test_invalid_selection_rejected(facade: ModelTrainingFacade):
    with pytest.raises(InvalidTrainingRequestError):
        facade.train_models(
            TrainModelsRequest(
                property_id="property-001",
                mode=TrainingMode.RETRAIN_SELECTED.value,
                slots=[
                    ModelSlot(
                        family="time_series",
                        scope="property",
                        granularity="annual",
                        target="milk_production_liters",
                        property_id="property-001",
                    )
                ],
            )
        )


def test_concurrency_conflict(facade: ModelTrainingFacade):
    facade.run_store.acquire_locks(
        ["regression|monthly|milk_production_liters|global"], "lock-holder"
    )
    try:
        with pytest.raises(TrainingConflictError):
            facade.train_models(
                TrainModelsRequest(
                    property_id="property-001",
                    mode=TrainingMode.RETRAIN_SELECTED.value,
                    slots=[
                        ModelSlot(
                            family="regression",
                            scope="global",
                            granularity="monthly",
                            target="milk_production_liters",
                        )
                    ],
                )
            )
    finally:
        facade.run_store.release_locks("lock-holder")


def test_source_unavailable(tmp_path: Path):
    base = Path(__file__).resolve().parents[1]
    cfg = load_config(base / "configs" / "training.yaml")
    cfg["paths"]["artifacts_dir"] = str(tmp_path / "artifacts")
    cfg["paths"]["processed_data_dir"] = str(tmp_path / "processed")
    cfg["data_source"] = {"type": "csv", "path": str(tmp_path / "missing.csv")}
    cfg["_meta"] = {"config_path": str(base / "configs" / "training.yaml"), "config_sha256": "x"}
    facade = ModelTrainingFacade(config=cfg, background=False)
    report = facade.get_model_availability("property-001")
    assert report.source_ok is False


def test_run_persistence(facade: ModelTrainingFacade):
    run = facade.ensure_models("property-001")
    loaded = facade.get_training_run(run.run_id)
    assert loaded.run_id == run.run_id
    listed = facade.list_training_runs("property-001")
    assert any(item.run_id == run.run_id for item in listed)
