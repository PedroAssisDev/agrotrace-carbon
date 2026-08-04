"""Utilitários de depreciação para APIs secundárias do módulo."""

from __future__ import annotations

import warnings

_WARNED: set[str] = set()


def warn_once(category: str, message: str, *, stacklevel: int = 3) -> None:
    if category in _WARNED:
        return
    _WARNED.add(category)
    warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)


def warn_secondary_api(name: str, preferred: str) -> None:
    warnings.warn(
        f"{name} é API secundária; prefira {preferred} para uso comum.",
        DeprecationWarning,
        stacklevel=3,
    )
