"""Erros específicos da camada de cálculos de emissões."""


class CalculationError(ValueError):
    """Erro base para entradas ou domínio inválidos nos cálculos."""


class TemporalInconsistencyError(CalculationError):
    """Combinação inválida entre escopo temporal e parâmetros (ex.: dias no período)."""
