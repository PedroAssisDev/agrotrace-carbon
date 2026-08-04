"""Logging técnico de consultas de previsão (não é aprovação/publicação)."""

from __future__ import annotations

import time
from typing import Any

from utils.logging_config import get_logger

logger = get_logger("agrotrace.forecast")


def log_forecast_event(
    *,
    forecast_type: str,
    property_id: str | None,
    success: bool,
    duration_seconds: float,
    granularity: str | None = None,
    expected_lactating_cows: int | None = None,
    model_ids: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    payload = {
        "forecast_type": forecast_type,
        "property_id": property_id,
        "granularity": granularity,
        "expected_lactating_cows": expected_lactating_cows,
        "model_ids": model_ids or {},
        "success": success,
        "duration_seconds": round(duration_seconds, 4),
        "error": error,
    }
    if success:
        logger.info("forecast_query %s", payload)
    else:
        logger.warning("forecast_query_failed %s", payload)


class timed_forecast:
    def __init__(self) -> None:
        self.started = 0.0
        self.elapsed = 0.0

    def __enter__(self) -> "timed_forecast":
        self.started = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.elapsed = time.perf_counter() - self.started
