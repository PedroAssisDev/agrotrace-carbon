"""Testes de resolução e isolamento de AGROTRACE_DATA_ROOT."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_default_data_root_is_frontend_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGROTRACE_DATA_ROOT", raising=False)
    import config

    config.apply_data_root(None, reset_runtime=False)
    assert config.DATA_DIR == (config.FRONTEND_DIR / "data").resolve()
    assert config.CYCLES_DIR == config.DATA_DIR / "cycles"
    assert config.PROV_DB_PATH == config.DATA_DIR / "db" / "provenance.db"
    assert config.BLOCKCHAIN_DB_PATH == config.DATA_DIR / "db" / "blockchain_service.db"
    assert config.SAVE_FILE_ORIGINALS_DIR == (
        config.SAVE_FILE_SERVICE_DIR / "data" / "originals"
    )
    assert not config.is_custom_data_root()


def test_custom_data_root_redirects_all_operational_paths(
    agrotrace_data_root: Path,
) -> None:
    import config

    assert config.DATA_DIR == agrotrace_data_root
    assert config.is_custom_data_root()
    assert config.CYCLES_DIR == agrotrace_data_root / "cycles"
    assert config.NORMALIZED_DIR == agrotrace_data_root / "normalized"
    assert config.ONTOLOGY_EXPORTS_DIR == agrotrace_data_root / "ontology_exports"
    assert config.PUBLICATIONS_DIR == agrotrace_data_root / "publications"
    assert config.EVIDENCE_PACKAGES_DIR == agrotrace_data_root / "evidence_packages"
    assert config.LOGS_DIR == agrotrace_data_root / "logs"
    assert config.PROV_DB_PATH == agrotrace_data_root / "db" / "provenance.db"
    assert config.BLOCKCHAIN_DB_PATH == agrotrace_data_root / "db" / "blockchain_service.db"
    assert config.SAVE_FILE_ORIGINALS_DIR == agrotrace_data_root / "save_file" / "originals"
    assert config.SAVE_FILE_EMULATED_UPLOADS_DIR == (
        agrotrace_data_root / "save_file" / "emulated_uploads"
    )
    assert config.MODEL_TRAINING_ARTIFACTS_DIR == (
        agrotrace_data_root / "model_training" / "artifacts"
    )
    assert config.MODEL_TRAINING_PROCESSED_DIR == (
        agrotrace_data_root / "model_training" / "processed"
    )
    assert config.MODEL_REGISTRY_PATH == (
        agrotrace_data_root / "model_training" / "artifacts" / "registry.jsonl"
    )


def test_isolation_between_two_data_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import config
    from utils.file_helpers import get_cycle, list_cycles, save_cycle

    real_cycles = (config.FRONTEND_DIR / "data" / "cycles").resolve()
    before_real = {p.name for p in real_cycles.glob("*.json")} if real_cycles.exists() else set()
    previous_env = monkeypatch.delenv("AGROTRACE_DATA_ROOT", raising=False)

    root_a = (tmp_path / "root-a").resolve()
    root_b = (tmp_path / "root-b").resolve()

    try:
        monkeypatch.setenv("AGROTRACE_DATA_ROOT", str(root_a))
        config.apply_data_root(root_a, reset_runtime=True)
        save_cycle(
            {
                "cycle_id": "CYCLE-ISO-A",
                "property_id": "PROP-A",
                "reporting_period": "2026-01",
                "current_status": "DRAFT",
            }
        )
        assert (root_a / "cycles" / "CYCLE-ISO-A.json").exists()
        assert get_cycle("CYCLE-ISO-A") is not None
        ids_a = {c["cycle_id"] for c in list_cycles()}
        assert "CYCLE-ISO-A" in ids_a

        monkeypatch.setenv("AGROTRACE_DATA_ROOT", str(root_b))
        config.apply_data_root(root_b, reset_runtime=True)
        assert get_cycle("CYCLE-ISO-A") is None
        save_cycle(
            {
                "cycle_id": "CYCLE-ISO-B",
                "property_id": "PROP-B",
                "reporting_period": "2026-02",
                "current_status": "DRAFT",
            }
        )
        assert (root_b / "cycles" / "CYCLE-ISO-B.json").exists()
        assert not (root_b / "cycles" / "CYCLE-ISO-A.json").exists()
        ids_b = {c["cycle_id"] for c in list_cycles()}
        assert ids_b == {"CYCLE-ISO-B"}

        # Não tocou frontend/data real
        after_real = {p.name for p in real_cycles.glob("*.json")} if real_cycles.exists() else set()
        assert after_real == before_real
        assert not (real_cycles / "CYCLE-ISO-A.json").exists()
        assert not (real_cycles / "CYCLE-ISO-B.json").exists()

        # Volta a A e ainda encontra o ciclo
        config.apply_data_root(root_a, reset_runtime=True)
        loaded = get_cycle("CYCLE-ISO-A")
        assert loaded is not None
        assert loaded["property_id"] == "PROP-A"
    finally:
        monkeypatch.delenv("AGROTRACE_DATA_ROOT", raising=False)
        config.apply_data_root(None, reset_runtime=True)
        _ = previous_env



def test_file_helpers_follow_config_attribute_not_frozen_import(
    agrotrace_data_root: Path,
) -> None:
    from utils.file_helpers import save_cycle

    save_cycle({"cycle_id": "CYCLE-ATTR", "property_id": "P1", "reporting_period": "2026-03"})
    path = agrotrace_data_root / "cycles" / "CYCLE-ATTR.json"
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["cycle_id"] == "CYCLE-ATTR"
