"""Structured JSON logging using structlog.

Every log line includes ``service``, ``environment`` and (when available)
``correlation_id``, which is propagated via ``contextvars`` from the request
middleware so that all logs of a single request share the same id.
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import EventDict, Processor

_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def bind_correlation_id(correlation_id: str | None) -> None:
    """Bind a correlation id to the current async/sync context."""
    _correlation_id_var.set(correlation_id)


def get_current_correlation_id() -> str | None:
    """Return the correlation id of the current context (or ``None``)."""
    return _correlation_id_var.get()


def _inject_correlation_id(_: Any, __: str, event_dict: EventDict) -> EventDict:
    cid = _correlation_id_var.get()
    if cid is not None:
        event_dict.setdefault("correlation_id", cid)
    return event_dict


def configure_logging(*, service_name: str, environment: str, level: str = "INFO") -> None:
    """Configure stdlib logging and structlog with a JSON renderer.

    Idempotent: safe to call multiple times (e.g. tests).
    """

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        _inject_correlation_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Quiet down noisy libraries by default.
    for noisy in ("uvicorn.access", "sqlalchemy.engine.Engine"):
        logging.getLogger(noisy).setLevel(max(logging.WARNING, root.level))

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service_name, environment=environment)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.stdlib.get_logger(name) if name else structlog.stdlib.get_logger()
