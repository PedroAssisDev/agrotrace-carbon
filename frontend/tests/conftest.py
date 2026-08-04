"""Fixtures compartilhadas do frontend — isolamento de data root."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def agrotrace_data_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Cria árvore temporária e aplica como AGROTRACE_DATA_ROOT via config central."""
    import config

    previous = os.environ.get("AGROTRACE_DATA_ROOT")
    root = (tmp_path / "agrotrace-data").resolve()
    monkeypatch.setenv("AGROTRACE_DATA_ROOT", str(root))
    config.apply_data_root(root, reset_runtime=True)

    for name in (
        "cycles",
        "normalized",
        "ontology_exports",
        "publications",
        "evidence_packages",
        "db",
        "logs",
        "save_file/originals",
        "save_file/emulated_uploads",
    ):
        (root / name).mkdir(parents=True, exist_ok=True)

    yield root

    if previous is None:
        monkeypatch.delenv("AGROTRACE_DATA_ROOT", raising=False)
        config.apply_data_root(None, reset_runtime=True)
    else:
        monkeypatch.setenv("AGROTRACE_DATA_ROOT", previous)
        config.apply_data_root(previous, reset_runtime=True)
