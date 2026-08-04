"""TemporalScope: monthly | annual (yearly aceito só na leitura)."""

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
    # Compatibilidade de leitura legada — não usar em novos dados.
    YEARLY = "annual"


def normalize_temporal_label(label: str) -> TemporalScope:
    """
    Converte rótulos aceitos para :class:`TemporalScope`.

    Aceita: ``monthly``, ``mensal``, ``yearly`` (legado), ``annual``, ``anual``.
    """
    if label is None or (isinstance(label, str) and not label.strip()):
        raise CalculationError(
            "O escopo temporal é obrigatório. Esperado um de: "
            "'monthly', 'mensal', 'annual', 'anual' (ou legado 'yearly')."
        )
    key = str(label).strip().lower()
    aliases = {
        "monthly": TemporalScope.MONTHLY,
        "mensal": TemporalScope.MONTHLY,
        "yearly": TemporalScope.ANNUAL,
        "annual": TemporalScope.ANNUAL,
        "anual": TemporalScope.ANNUAL,
    }
    if key not in aliases:
        raise CalculationError(
            f"Escopo temporal inválido: {label!r}. "
            "Esperado: 'monthly'/'mensal' ou 'annual'/'anual' (legado: 'yearly')."
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
    # Normaliza YEARLY legado → ANNUAL
    normalized = [
        TemporalScope.ANNUAL if s in (TemporalScope.ANNUAL, TemporalScope.YEARLY) or s.value == "annual" else s
        for s in scopes
    ]
    first = normalized[0]
    for s in normalized[1:]:
        if s != first:
            msg = (
                "Inconsistência temporal: componentes com granularidades diferentes "
                f"({first.value!r} vs {s.value!r})."
            )
            if context:
                msg = f"{context} {msg}"
            raise TemporalInconsistencyError(msg)
    return first
