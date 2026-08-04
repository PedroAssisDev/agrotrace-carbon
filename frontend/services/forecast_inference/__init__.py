"""Camada de inferência de previsões (consumo dos artefatos do model-training-service)."""

from services.forecast_inference.facade import PredictionFacade, get_prediction_facade
from services.forecast_inference.errors import (
    ForecastInferenceError,
    InvalidInputError,
    ModelNotFoundError,
    OutOfDomainPredictionError,
    RegistryEmptyError,
    RegistryNotFoundError,
)
from services.forecast_inference.types import (
    Prediction,
    PredictionNotPublishableError,
    is_prediction_payload,
    prediction_from_inference_dict,
)

__all__ = [
    "PredictionFacade",
    "get_prediction_facade",
    "ForecastInferenceError",
    "InvalidInputError",
    "ModelNotFoundError",
    "OutOfDomainPredictionError",
    "RegistryEmptyError",
    "RegistryNotFoundError",
    "Prediction",
    "PredictionNotPublishableError",
    "is_prediction_payload",
    "prediction_from_inference_dict",
]
