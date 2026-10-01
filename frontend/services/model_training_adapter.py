"""Adapter in-process para ModelTrainingFacade (frontend nao treina)."""

from __future__ import annotations

import logging
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import config
from services.training_data_export_service import (
    approved_results_export_path,
    export_approved_results_from_cycles,
)

logger = logging.getLogger("agrotrace.model_training_adapter")

_GLOBAL_WARNING = (
    "Os modelos de regressao sao globais. O retreinamento utilizara os dados "
    "aprovados de todas as propriedades e podera alterar o modelo ativo "
    "utilizado pelas demais propriedades."
)


def _ensure_path() -> None:
    src = str(config.MODEL_TRAINING_SRC_DIR.resolve())
    if src not in sys.path:
        sys.path.insert(0, src)


def refresh_training_source(*, force: bool = False) -> dict[str, Any]:
    """Exporta ciclos publicados para o CSV canônico consumido pelo treino."""
    path = approved_results_export_path()
    try:
        if not force and not path.exists():
            force = True
        result = export_approved_results_from_cycles(output_path=path)
        return {"ok": True, **result}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[TRAIN_EXPORT] falha ao atualizar fonte: %s", exc)
        return {
            "ok": False,
            "error": str(exc),
            "path": str(path),
            "row_count": 0,
            "properties": [],
            "skipped": 0,
        }


def _build_facade_config() -> dict[str, Any]:
    _ensure_path()
    from model_training_service.config import load_config

    csv_path = approved_results_export_path()
    if not csv_path.exists():
        refresh_training_source(force=True)

    cfg = load_config(config.MODEL_TRAINING_CONFIG_PATH)
    cfg.setdefault("data_source", {})
    cfg["data_source"]["type"] = "csv"
    cfg["data_source"]["path"] = str(csv_path.resolve())
    cfg.setdefault("paths", {})
    cfg["paths"]["processed_data_dir"] = str(Path(config.MODEL_TRAINING_PROCESSED_DIR).resolve())
    cfg["paths"]["artifacts_dir"] = str(Path(config.MODEL_TRAINING_ARTIFACTS_DIR).resolve())
    return cfg


@lru_cache(maxsize=1)
def _facade():
    _ensure_path()
    from model_training_service.api.facade import ModelTrainingFacade

    return ModelTrainingFacade(config=_build_facade_config(), background=True)


def reset_facade() -> None:
    """Invalida o singleton (ex.: apos mudanca de data root)."""
    _facade.cache_clear()


def _facade_ready() -> Any:
    """Garante CSV atualizado e facade apontando para paths do frontend."""
    refresh_training_source()
    return _facade()


def get_model_availability(property_id: str) -> dict[str, Any]:
    try:
        report = _facade_ready().get_model_availability(property_id)
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
        return _facade_ready().get_training_eligibility(property_id)
    except Exception as exc:  # noqa: BLE001
        return {"property_id": property_id, "source_ok": False, "source_error": str(exc), "items": []}


def list_training_runs(property_id: str | None = None) -> list[dict[str, Any]]:
    try:
        return [r.to_dict() for r in _facade_ready().list_training_runs(property_id)]
    except Exception:
        return []


def get_training_run(run_id: str) -> dict[str, Any] | None:
    try:
        return _facade_ready().get_training_run(run_id).to_dict()
    except Exception:
        return None


def ensure_missing_models(property_id: str, **kwargs) -> dict[str, Any]:
    record = _facade_ready().ensure_models(property_id, **kwargs)
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
    return _facade_ready().train_models(request).to_dict()


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
    return _facade_ready().train_models(request).to_dict()


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
