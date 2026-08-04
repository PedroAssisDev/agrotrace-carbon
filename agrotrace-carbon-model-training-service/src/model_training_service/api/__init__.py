"""API pública do model-training-service."""

from model_training_service.api.contracts import (
    ModelAvailabilityReport,
    ModelSlot,
    TrainModelsRequest,
    TrainingRunRecord,
)
from model_training_service.api.facade import ModelTrainingFacade, get_default_facade
from model_training_service.domain.enums import TrainingMode

__all__ = [
    "ModelTrainingFacade",
    "get_default_facade",
    "TrainModelsRequest",
    "ModelSlot",
    "ModelAvailabilityReport",
    "TrainingRunRecord",
    "TrainingMode",
]
