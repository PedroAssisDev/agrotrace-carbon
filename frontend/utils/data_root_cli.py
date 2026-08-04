"""CLI helper para ``--data-root`` sem espalhar leituras de ``os.environ``.

Os scripts chamam ``apply_data_root_from_argv()`` antes de ``bootstrap_all()``.
A variável ``AGROTRACE_DATA_ROOT`` continua sendo lida apenas em ``config.py``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import config


def add_data_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-root",
        type=str,
        default=None,
        help=(
            "Diretório isolado para artefatos operacionais "
            "(equivale a AGROTRACE_DATA_ROOT; não altera frontend/data real)."
        ),
    )


def apply_data_root_option(data_root: str | Path | None) -> Path | None:
    """Aplica data root explícito via config central. Retorna o root se aplicado."""
    if data_root is None:
        return None
    return config.apply_data_root(data_root)


def apply_data_root_from_argv(argv: list[str] | None = None) -> Path | None:
    """Consome ``--data-root PATH`` de argv e aplica via ``config.apply_data_root``.

    Remove o argumento de ``sys.argv`` quando ``argv`` não é passado, para não
    interferir em parsers dos scripts.
    """
    source = list(sys.argv[1:] if argv is None else argv)
    root: str | None = None
    cleaned: list[str] = []
    i = 0
    while i < len(source):
        token = source[i]
        if token == "--data-root" and i + 1 < len(source):
            root = source[i + 1]
            i += 2
            continue
        if token.startswith("--data-root="):
            root = token.split("=", 1)[1]
            i += 1
            continue
        cleaned.append(token)
        i += 1

    if argv is None:
        sys.argv = [sys.argv[0], *cleaned]

    return apply_data_root_option(root)
