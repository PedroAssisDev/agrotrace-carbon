"""Registry: layout_id duplicado e aviso em log."""

from __future__ import annotations

import logging
from pathlib import Path
from textwrap import dedent

import pytest

from wrappers.registry.file_registry import LayoutRegistry


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(dedent(text).strip() + "\n", encoding="utf-8")


def test_duplicate_layout_id_last_wins_and_logs_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    root = tmp_path / "layouts"
    yaml_a = root / "fam_a" / "v1" / "layout.yaml"
    yaml_b = root / "fam_b" / "v1" / "layout.yaml"
    minimal = """
    layout_id: dup:test
    layout_family: fam
    version: "1.0"
    status: active
    physical:
      format: csv
      delimiter: ","
      encoding: utf-8
    granularity:
      temporal: instant
      organizational: property
    schema:
      fields: []
    validation_rules: []
    """
    _write(yaml_a, minimal)
    _write(yaml_b, minimal)

    with caplog.at_level(logging.WARNING):
        reg = LayoutRegistry(layouts_root=root)

    assert "dup:test" in reg.list_layout_ids()
    assert any("duplicado" in r.message.lower() for r in caplog.records)
