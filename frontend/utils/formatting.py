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


def format_kg_co2e(value: Any) -> str:
    """Alias canônico para emissão em kg CO₂e."""
    return format_co2e(value)


def format_co2e_t(value: Any, decimals: int = 2) -> str:
    """Formata emissão em toneladas CO₂e."""
    return f"{format_number(value, decimals)} t CO₂e"


def format_t_co2e(value: Any) -> str:
    """Alias canônico para emissão em t CO₂e."""
    return format_co2e_t(value)


def format_liters(value: Any) -> str:
    """Formata produção de leite em litros."""
    return f"{format_number(value, 0)} L"


def format_intensity(value: Any) -> str:
    """Formata intensidade kg CO₂e/L."""
    return f"{format_number(value, 4)} kg CO₂e/L"


def format_intensity_kg_co2e_per_l(value: Any) -> str:
    """Alias canônico para intensidade kg CO₂e/L."""
    return format_intensity(value)


def format_percent(value: Any, decimals: int = 1) -> str:
    """Formata percentual."""
    try:
        return f"{format_number(value, decimals)}%"
    except (TypeError, ValueError):
        return str(value) if value is not None else "—"


def format_count(value: Any) -> str:
    """Formata contagem inteira sem decimal."""
    try:
        return f"{int(round(float(value))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(value) if value is not None else "—"


def format_hash_short(value: Any, length: int = 12) -> str:
    """Formata hash truncado para exibição."""
    from utils.hash_helpers import truncate_hash

    return truncate_hash(str(value) if value is not None else "", length=length)


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
