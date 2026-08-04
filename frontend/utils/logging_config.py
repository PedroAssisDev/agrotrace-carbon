"""Configuração central de logs do protótipo frontend."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from config import DATA_DIR

LOG_LEVEL = os.getenv("AGROTRACE_LOG_LEVEL", "DEBUG").upper()
LOG_FILE = os.getenv("AGROTRACE_LOG_FILE", str(DATA_DIR / "logs" / "agrotrace.log"))

_CONFIGURED = False


def setup_logging() -> None:
    """Inicializa handlers de console + arquivo (idempotente)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, LOG_LEVEL, logging.DEBUG)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        stream = logging.StreamHandler(sys.stdout)
        stream.setFormatter(logging.Formatter(fmt))
        root.addHandler(stream)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(file_handler)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("dash").setLevel(logging.INFO)

    _CONFIGURED = True
    logging.getLogger("agrotrace.app").info(
        "Logging configurado level=%s file=%s",
        LOG_LEVEL,
        log_path,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
