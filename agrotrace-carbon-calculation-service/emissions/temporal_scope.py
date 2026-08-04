"""TemporalScope: monthly | annual."""

from __future__ import annotations

from enum import Enum

from emissions.exceptions import CalculationError, TemporalInconsistencyError


class TemporalScope(str, Enum):
    """
    Granularidade temporal permitida para entradas e resultados.

    Valores canônicos: ``monthly`` e ``annual``.
    """

    MONTHLY = "monthly"
    ANNUAL = "annual"


def normalize_temporal_label(label: str) -> TemporalScope:
    """
    Converte rótulos aceitos para :class:`TemporalScope`.

    Aceita: ``monthly``, ``mensal``, ``annual``, ``anual``.
    """
    if label is None or (isinstance(label, str) and not label.strip()):
        raise CalculationError(
            "O escopo temporal é obrigatório. Esperado um de: "
            "'monthly', 'mensal', 'annual', 'anual'."
        )
    key = str(label).strip().lower()
    aliases = {
        "monthly": TemporalScope.MONTHLY,
        "mensal": TemporalScope.MONTHLY,
        "annual": TemporalScope.ANNUAL,
        "anual": TemporalScope.ANNUAL,
    }
    if key not in aliases:
        raise CalculationError(
            f"Escopo temporal inválido: {label!r}. "
            "Esperado: 'monthly'/'mensal' ou 'annual'/'anual'."
        )
    return aliases[key]


def require_matching_scope(
    *scopes: TemporalScope,
    context: str = "",
) -> TemporalScope:
    """
    Garante que todos os escopos passados são idênticos.

    Raises:
        TemporalInconsistencyError: se houver mistura de granularidades.
    """
    if not scopes:
        raise CalculationError("require_matching_scope: nenhum escopo foi informado.")
    first = scopes[0]
    for s in scopes[1:]:
        if s != first:
            msg = (
                "Inconsistência temporal: componentes com granularidades diferentes "
                f"({first.value!r} vs {s.value!r})."
            )
            if context:
                msg = f"{context} {msg}"
            raise TemporalInconsistencyError(msg)
    return first
