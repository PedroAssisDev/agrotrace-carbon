"""Helpers de log para callbacks Dash."""

from __future__ import annotations

import json
import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar

from dash import ctx, no_update

logger = logging.getLogger("agrotrace.callbacks")

F = TypeVar("F", bound=Callable[..., Any])


def safe_repr(obj: Any, max_len: int = 800) -> str:
    if obj is no_update:
        return "<no_update>"
    try:
        text = json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = repr(obj)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def log_callback(name: str) -> Callable[[F], F]:
    """Decorator: loga trigger, duração e resultado; repropaga exceções."""

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            trigger = getattr(ctx, "triggered_id", None)
            logger.debug("[%s] trigger=%s", name, trigger)
            started = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                duration_ms = round((time.perf_counter() - started) * 1000.0, 1)
                if isinstance(result, tuple):
                    logger.debug(
                        "[%s] ok outputs=%d first=%s duration_ms=%.1f",
                        name,
                        len(result),
                        safe_repr(result[0], 400),
                        duration_ms,
                    )
                else:
                    logger.debug(
                        "[%s] ok result=%s duration_ms=%.1f",
                        name,
                        safe_repr(result, 400),
                        duration_ms,
                    )
                return result
            except Exception:
                duration_ms = round((time.perf_counter() - started) * 1000.0, 1)
                logger.exception("[%s] FAILED trigger=%s duration_ms=%.1f", name, trigger, duration_ms)
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


def log_filter_summary(prefix: str, gf: dict | None) -> None:
    """Log compacto do estado normalizado do filtro global."""
    if not gf:
        logger.debug("%s empty", prefix)
        return
    logger.info(
        "%s farm=%s cycle=%s period=%s start=%s end=%s view=%s mode=%s",
        prefix,
        gf.get("farm_id"),
        gf.get("cycle_id"),
        gf.get("period"),
        gf.get("analysis_period_start"),
        gf.get("analysis_period_end"),
        gf.get("view_granularity"),
        gf.get("data_mode"),
    )
