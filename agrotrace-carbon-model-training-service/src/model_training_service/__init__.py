"""CarbonSECO model training service."""

__version__ = "0.1.0"

from model_training_service.api import ModelTrainingFacade, TrainModelsRequest, TrainingMode

__all__ = ["ModelTrainingFacade", "TrainModelsRequest", "TrainingMode", "__version__"]
