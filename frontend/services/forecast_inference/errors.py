"""Exceções tipadas da camada de inferência de previsões."""

from __future__ import annotations


class ForecastInferenceError(Exception):
    """Erro base da camada de inferência."""


class RegistryNotFoundError(ForecastInferenceError):
    """registry.jsonl inexistente ou ilegível."""


class RegistryEmptyError(ForecastInferenceError):
    """Registry sem entradas válidas."""


class ModelNotFoundError(ForecastInferenceError):
    """Nenhum modelo compatível encontrado."""


class ArtifactCorruptError(ForecastInferenceError):
    """Artefato ausente, ilegível ou inconsistente."""


class MetadataIncompatibleError(ForecastInferenceError):
    """Metadados incompatíveis com o contrato esperado."""


class InvalidInputError(ForecastInferenceError):
    """Entrada do usuário inválida."""


class OutOfDomainPredictionError(ForecastInferenceError):
    """Previsão não finita ou fora do domínio (ex.: negativa)."""
