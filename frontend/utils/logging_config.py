"""Configuração central de logs do protótipo frontend."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import config

LOG_LEVEL = os.getenv("AGROTRACE_LOG_LEVEL", "DEBUG").upper()

_CONFIGURED = False
_FILE_HANDLER: logging.Handler | None = None


def _default_log_file() -> str:
    return str(config.LOGS_DIR / "agrotrace.log")


def get_log_file() -> str:
    """Caminho efetivo do arquivo de log (env ou data root)."""
    return os.getenv("AGROTRACE_LOG_FILE", _default_log_file())


# Compat: módulos que leem LOG_FILE no import
LOG_FILE = get_log_file()


def reset_logging_for_data_root() -> None:
    """Permite reconfigurar o handler de arquivo após troca de data root."""
    global _CONFIGURED, _FILE_HANDLER, LOG_FILE
    root = logging.getLogger()
    if _FILE_HANDLER is not None:
        root.removeHandler(_FILE_HANDLER)
        try:
            _FILE_HANDLER.close()
        except Exception:
            pass
        _FILE_HANDLER = None
    _CONFIGURED = False
    LOG_FILE = get_log_file()


def setup_logging() -> None:
    """Inicializa handlers de console + arquivo (idempotente)."""
    global _CONFIGURED, _FILE_HANDLER, LOG_FILE
    if _CONFIGURED:
        return

    LOG_FILE = get_log_file()
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
    _FILE_HANDLER = file_handler

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
