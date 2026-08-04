class ModelTrainingError(Exception):
    """Base exception for the module."""


class DataValidationError(ModelTrainingError):
    """Raised when the input data violates the canonical contract."""


class InsufficientDataError(ModelTrainingError):
    """Raised when there are not enough valid observations to train a model."""


class CandidateTrainingError(ModelTrainingError):
    """Raised when no candidate model can be trained successfully."""


class TrainingConflictError(ModelTrainingError):
    """Raised when a conflicting training run is already active for a slot."""

    def __init__(self, message: str, *, run_id: str | None = None) -> None:
        super().__init__(message)
        self.run_id = run_id


class InvalidTrainingRequestError(ModelTrainingError):
    """Raised when a training request violates domain constraints."""


class DataSourceUnavailableError(ModelTrainingError):
    """Raised when the configured approved-results source cannot be loaded."""
