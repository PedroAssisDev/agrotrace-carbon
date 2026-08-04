"""Intercepta escritas fora do AGROTRACE_DATA_ROOT temporário."""

from __future__ import annotations

import builtins
import os
from pathlib import Path

import pytest


FORBIDDEN_SUFFIXES = (
    Path("frontend") / "data",
    Path("agrotrace-carbon-save-file") / "data" / "originals",
    Path("agrotrace-carbon-save-file") / "data" / "emulated_uploads",
    Path("agrotrace-carbon-model-training-service") / "artifacts",
)


@pytest.fixture
def write_tracker(monkeypatch: pytest.MonkeyPatch, agrotrace_data_root: Path):
    """Patch Path.write_text / write_bytes / open(w) e coleta caminhos escritos."""
    observed: list[str] = []
    root = agrotrace_data_root.resolve()
    workspace = Path(__file__).resolve().parents[2]
    real_write_text = Path.write_text
    real_write_bytes = Path.write_bytes
    real_open = builtins.open

    def _record(path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        observed.append(str(resolved))

    def _is_forbidden(path: Path) -> bool:
        try:
            resolved = path.resolve()
        except OSError:
            return False
        # Permitido: sob o data root temporário
        try:
            resolved.relative_to(root)
            return False
        except ValueError:
            pass
        # Permitido: pytest/tmp fora do workspace
        try:
            resolved.relative_to(workspace)
        except ValueError:
            return False
        for suffix in FORBIDDEN_SUFFIXES:
            marker = (workspace / suffix).resolve()
            try:
                resolved.relative_to(marker)
                return True
            except ValueError:
                continue
            # também: qualquer path que contenha o segmento legado
        text = str(resolved).replace("\\", "/")
        if "/frontend/data/" in text and str(root).replace("\\", "/") not in text:
            return True
        if "/agrotrace-carbon-save-file/data/originals" in text:
            return True
        if "/agrotrace-carbon-save-file/data/emulated_uploads" in text:
            return True
        if "/agrotrace-carbon-model-training-service/artifacts" in text:
            return True
        return False

    def patched_write_text(self: Path, *args, **kwargs):
        _record(self)
        if _is_forbidden(self):
            raise AssertionError(f"Escrita fora do data root: {self}")
        return real_write_text(self, *args, **kwargs)

    def patched_write_bytes(self: Path, *args, **kwargs):
        _record(self)
        if _is_forbidden(self):
            raise AssertionError(f"Escrita fora do data root: {self}")
        return real_write_bytes(self, *args, **kwargs)

    def patched_open(file, mode="r", *args, **kwargs):
        path = Path(file) if not isinstance(file, int) else None
        if path is not None and any(m in str(mode) for m in ("w", "a", "x", "+")):
            _record(path)
            if _is_forbidden(path):
                raise AssertionError(f"Escrita fora do data root: {path}")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", patched_write_text)
    monkeypatch.setattr(Path, "write_bytes", patched_write_bytes)
    monkeypatch.setattr(builtins, "open", patched_open)

    yield observed, root

    print("\n=== Escritas observadas ===")
    for p in observed:
        print(p)


def test_save_original_without_dest_dir_stays_under_root(write_tracker) -> None:
    observed, root = write_tracker
    import sys
    import config

    save_root = str(config.SAVE_FILE_SERVICE_DIR.resolve())
    if save_root not in sys.path:
        sys.path.insert(0, save_root)

    from save_file.storage import default_originals_dir, save_original_content

    assert default_originals_dir().resolve() == (root / "save_file" / "originals").resolve()
    meta = save_original_content(
        b"col_a,col_b\n1,2\n",
        property_id="FARM-ISO",
        reporting_period="2026-01",
        original_filename="iso-test.csv",
        dest_dir=None,
    )
    stored = Path(meta["stored_path"]).resolve()
    assert str(stored).startswith(str(root.resolve()))
    assert "frontend" not in str(stored).replace("\\", "/").split("/data/")[0] or str(root) in str(stored)


def test_mock_paths_not_frontend_data_literal(agrotrace_data_root: Path) -> None:
    from services.mock_data import mock_full_cycle, mock_pending_cycle

    full = mock_full_cycle()
    pending = mock_pending_cycle()
    for c in (full, pending):
        path = (c.get("raw_file") or {}).get("stored_path") or ""
        assert "frontend/data/" not in path.replace("\\", "/")
        assert "raw_originals" in path.replace("\\", "/")


def test_model_training_artifacts_under_root(agrotrace_data_root: Path) -> None:
    import config

    assert config.MODEL_TRAINING_ARTIFACTS_DIR.resolve().is_relative_to(agrotrace_data_root.resolve())
    probe = config.MODEL_TRAINING_ARTIFACTS_DIR / "isolation_probe.txt"
    probe.write_text("ok", encoding="utf-8")
    assert probe.exists()
    assert probe.resolve().is_relative_to(agrotrace_data_root.resolve())


def test_emulated_default_under_root(agrotrace_data_root: Path) -> None:
    import sys
    import config

    save_root = str(config.SAVE_FILE_SERVICE_DIR.resolve())
    if save_root not in sys.path:
        sys.path.insert(0, save_root)
    from save_file.emulated.manifest import default_emulated_dir

    assert default_emulated_dir().resolve() == (
        agrotrace_data_root / "save_file" / "emulated_uploads"
    ).resolve()
