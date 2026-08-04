"""Validações compartilhadas para parâmetros de cálculo."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import TypeVar

from emissions.exceptions import CalculationError, TemporalInconsistencyError
from emissions.temporal_scope import TemporalScope

K = TypeVar("K")
V = TypeVar("V")


def require_non_negative(name: str, value: float) -> None:
    """Exige número finito e não negativo."""
    if value is None:
        raise CalculationError(
            f"A variável {name!r} é obrigatória e não pode ser None."
        )
    if not isinstance(value, (int, float)):
        raise CalculationError(
            f"A variável {name!r} deve ser numérica; recebido {type(value).__name__}."
        )
    if not float("-inf") < float(value) < float("inf"):
        raise CalculationError(f"A variável {name!r} deve ser finita; recebido {value!r}.")
    if math.isnan(float(value)):
        raise CalculationError(f"A variável {name!r} não pode ser NaN.")
    if float(value) < 0:
        raise CalculationError(
            f"A variável {name!r} não pode ser negativa; recebido {value!r}."
        )


def require_positive_int(name: str, value: int) -> None:
    """Exige inteiro >= 1."""
    if value is None:
        raise CalculationError(f"A variável {name!r} é obrigatória e não pode ser None.")
    if not isinstance(value, int) or isinstance(value, bool):
        raise CalculationError(
            f"A variável {name!r} deve ser um inteiro; recebido {type(value).__name__}."
        )
    if value < 1:
        raise CalculationError(
            f"A variável {name!r} deve ser >= 1 (dias no período); recebido {value!r}."
        )


def require_same_keys(
    left: Mapping[K, V],
    right: Mapping[K, V],
    left_label: str,
    right_label: str,
) -> None:
    """Garante que dois mapeamentos têm exatamente o mesmo conjunto de chaves."""
    a, b = set(left.keys()), set(right.keys())
    if a != b:
        only_left = sorted(str(x) for x in (a - b))
        only_right = sorted(str(x) for x in (b - a))
        raise CalculationError(
            f"Chaves inconsistentes entre {left_label} e {right_label}: "
            f"só em {left_label}: {only_left}; só em {right_label}: {only_right}."
        )


def validate_days_in_period(temporal_scope: TemporalScope, days_in_period: int) -> None:
    """
    Valida ``days_in_period`` em função do escopo temporal.

    - Mensal: esperado entre 1 e 31 (um mês civil ou período mensal declarado).
    - Anual: esperado entre 360 e 366 (ano civil ou período anual declarado).

    Raises:
        TemporalInconsistencyError: se o número de dias não for plausível para o escopo.
    """
    require_positive_int("days_in_period", days_in_period)
    if temporal_scope is TemporalScope.MONTHLY:
        if days_in_period > 31:
            raise TemporalInconsistencyError(
                f"Para temporal_scope={temporal_scope.value!r}, days_in_period deve ser "
                f"<= 31 (período mensal); recebido {days_in_period!r}."
            )
    elif temporal_scope is TemporalScope.YEARLY:
        if days_in_period < 360:
            raise TemporalInconsistencyError(
                f"Para temporal_scope={temporal_scope.value!r}, days_in_period deve ser "
                f">= 360 (período anual típico); recebido {days_in_period!r}."
            )


def validate_mapping_non_negative(
    mapping: Mapping[str, float],
    label: str,
) -> None:
    """Valida que todos os valores do mapeamento são não negativos."""
    for key, val in mapping.items():
        require_non_negative(f"{label}[{key!r}]", float(val))
