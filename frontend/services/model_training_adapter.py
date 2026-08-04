"""Adapter in-process para ModelTrainingFacade (frontend nao treina)."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import config

_GLOBAL_WARNING = (
    "Os modelos de regressao sao globais. O retreinamento utilizara os dados "
    "aprovados de todas as propriedades e podera alterar o modelo ativo "
    "utilizado pelas demais propriedades."
)


def _ensure_path() -> None:
    src = str(config.MODEL_TRAINING_SRC_DIR.resolve())
    if src not in sys.path:
        sys.path.insert(0, src)


@lru_cache(maxsize=1)
def _facade():
    _ensure_path()
    from model_training_service.api.facade import ModelTrainingFacade

    return ModelTrainingFacade(
        config_path=config.MODEL_TRAINING_CONFIG_PATH,
        background=True,
    )


def get_model_availability(property_id: str) -> dict[str, Any]:
    try:
        report = _facade().get_model_availability(property_id)
        return report.to_dict()
    except Exception as exc:  # noqa: BLE001
        return {
            "property_id": property_id,
            "data_summary": {},
            "models": [],
            "active_training_runs": [],
            "source_ok": False,
            "source_error": str(exc),
        }


def get_training_eligibility(property_id: str) -> dict[str, Any]:
    try:
        return _facade().get_training_eligibility(property_id)
    except Exception as exc:  # noqa: BLE001
        return {"property_id": property_id, "source_ok": False, "source_error": str(exc), "items": []}


def list_training_runs(property_id: str | None = None) -> list[dict[str, Any]]:
    try:
        return [r.to_dict() for r in _facade().list_training_runs(property_id)]
    except Exception:
        return []


def get_training_run(run_id: str) -> dict[str, Any] | None:
    try:
        return _facade().get_training_run(run_id).to_dict()
    except Exception:
        return None


def ensure_missing_models(property_id: str, **kwargs) -> dict[str, Any]:
    record = _facade().ensure_models(property_id, **kwargs)
    return record.to_dict()


def retrain_stale_models(property_id: str, **kwargs) -> dict[str, Any]:
    _ensure_path()
    from model_training_service.api.contracts import TrainModelsRequest
    from model_training_service.domain.enums import TrainingMode

    request = TrainModelsRequest(
        property_id=property_id,
        mode=TrainingMode.RETRAIN_STALE.value,
        **kwargs,
    )
    return _facade().train_models(request).to_dict()


def train_selected_models(
    property_id: str,
    slot_dicts: list[dict[str, Any]],
    **kwargs,
) -> dict[str, Any]:
    _ensure_path()
    from model_training_service.api.contracts import ModelSlot, TrainModelsRequest
    from model_training_service.domain.enums import TrainingMode

    slots = [ModelSlot.from_dict(item) for item in slot_dicts]
    request = TrainModelsRequest(
        property_id=property_id,
        mode=TrainingMode.RETRAIN_SELECTED.value,
        slots=slots,
        **kwargs,
    )
    return _facade().train_models(request).to_dict()


def global_retrain_warning() -> str:
    return _GLOBAL_WARNING


def slot_options() -> list[dict[str, Any]]:
    return [
        {
            "id": "reg-monthly-milk",
            "label": "Regressao mensal — producao",
            "family": "regression",
            "scope": "global",
            "granularity": "monthly",
            "target": "milk_production_liters",
            "property_id": None,
        },
        {
            "id": "reg-monthly-emis",
            "label": "Regressao mensal — emissao",
            "family": "regression",
            "scope": "global",
            "granularity": "monthly",
            "target": "total_ghg_emissions_tco2e",
            "property_id": None,
        },
        {
            "id": "reg-annual-milk",
            "label": "Regressao anual — producao",
            "family": "regression",
            "scope": "global",
            "granularity": "annual",
            "target": "milk_production_liters",
            "property_id": None,
        },
        {
            "id": "reg-annual-emis",
            "label": "Regressao anual — emissao",
            "family": "regression",
            "scope": "global",
            "granularity": "annual",
            "target": "total_ghg_emissions_tco2e",
            "property_id": None,
        },
        {
            "id": "ts-milk",
            "label": "Serie temporal mensal — producao",
            "family": "time_series",
            "scope": "property",
            "granularity": "monthly",
            "target": "milk_production_liters",
            "property_id": "__PROPERTY__",
        },
        {
            "id": "ts-emis",
            "label": "Serie temporal mensal — emissao",
            "family": "time_series",
            "scope": "property",
            "granularity": "monthly",
            "target": "total_ghg_emissions_tco2e",
            "property_id": "__PROPERTY__",
        },
    ]


def resolve_slot_selection(property_id: str, selected_ids: list[str]) -> list[dict[str, Any]]:
    by_id = {item["id"]: item for item in slot_options()}
    slots: list[dict[str, Any]] = []
    for sid in selected_ids or []:
        template = by_id.get(sid)
        if not template:
            continue
        slot = {
            "family": template["family"],
            "scope": template["scope"],
            "granularity": template["granularity"],
            "target": template["target"],
            "property_id": property_id if template["family"] == "time_series" else None,
        }
        slots.append(slot)
    return slots
