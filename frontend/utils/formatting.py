"""Formatação de valores para exibição."""

from __future__ import annotations

from typing import Any

NA = "não disponível"


def format_number(value: Any, decimals: int = 2) -> str:
    """Formata número com separador de milhar."""
    try:
        n = float(value)
        return f"{n:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return str(value) if value is not None else "—"


def format_co2e(value: Any) -> str:
    """Formata emissão em kg CO₂e."""
    return f"{format_number(value)} kg CO₂e"


def format_intensity(value: Any) -> str:
    """Formata intensidade kg CO₂e/L."""
    return f"{format_number(value, 4)} kg CO₂e/L"


def safe_get(data: dict | None, *keys: str, default: Any = None) -> Any:
    """Acesso seguro a dict aninhado."""
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current
