"""Helpers de observabilidade do pipeline (stdlib logging, key=value).

Não substitui eventos de proveniência em SQLite — apenas logs de aplicação
para acompanhar etapas, decisões, chamadas externas e duração.
"""

from __future__ import annotations

import logging
import time
from typing import Any

_SKIP = object()


def ids_from_cycle(cycle: dict | None) -> dict[str, Any]:
    """Extrai IDs comuns do ciclo para correlacionar logs."""
    if not cycle:
        return {}
    out: dict[str, Any] = {}
    for key, src in (
        ("cycle_id", "cycle_id"),
        ("pipeline_run_id", "pipeline_run_id"),
        ("property_id", "property_id"),
        ("period", "reporting_period"),
    ):
        val = cycle.get(src)
        if val is not None and val != "":
            out[key] = val
    return out


def truncate(value: Any, length: int = 12) -> str | None:
    if value is None or value == "":
        return None
    text = str(value)
    if len(text) <= length:
        return text
    return text[:length] + "…"


def format_kv(**fields: Any) -> str:
    """Serializa campos estáveis como ``k=v`` (omite None / _SKIP)."""
    parts: list[str] = []
    for key, value in fields.items():
        if value is None or value is _SKIP:
            continue
        if isinstance(value, float):
            parts.append(f"{key}={value:.1f}" if key.endswith("_ms") else f"{key}={value}")
        elif isinstance(value, bool):
            parts.append(f"{key}={'true' if value else 'false'}")
        else:
            text = str(value).replace("\n", " ").strip()
            if " " in text or "=" in text:
                text = text.replace('"', "'")
                parts.append(f'{key}="{text}"')
            else:
                parts.append(f"{key}={text}")
    return " ".join(parts)


def _emit(logger: logging.Logger, level: int, tag: str, event: str, **fields: Any) -> None:
    body = format_kv(**fields)
    if body:
        logger.log(level, "%s %s %s", tag, event, body)
    else:
        logger.log(level, "%s %s", tag, event)


def log_pipe(logger: logging.Logger, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    _emit(logger, level, "[PIPE]", event, **fields)


def log_call(logger: logging.Logger, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    _emit(logger, level, "[CALL]", event, **fields)


def log_decision(logger: logging.Logger, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    _emit(logger, level, "[DECISION]", event, **fields)


def log_fail(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.WARNING,
    **fields: Any,
) -> None:
    _emit(logger, level, "[FAIL]", event, **fields)


class timed_op:
    """Context manager que mede duração em milissegundos (``duration_ms``)."""

    def __init__(self) -> None:
        self.started = 0.0
        self.elapsed = 0.0

    @property
    def duration_ms(self) -> float:
        # Inclui early-return ainda dentro do ``with`` (elapsed ainda não fechado).
        base = self.elapsed if self.elapsed else (
            (time.perf_counter() - self.started) if self.started else 0.0
        )
        return round(base * 1000.0, 1)

    def __enter__(self) -> "timed_op":
        self.started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.elapsed = time.perf_counter() - self.started
