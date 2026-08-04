"""Testes RF002 — adapter de recuperação + AGROTRACE_DATA_ROOT."""

from __future__ import annotations

from pathlib import Path

import pytest

from services import save_file_adapter
from utils.file_helpers import save_cycle


def test_adapter_retrieve_by_cycle_id_roundtrip(agrotrace_data_root: Path) -> None:
    payload = b"rf002-adapter-bytes-exact\n"
    meta = save_file_adapter.save_uploaded_content(
        payload,
        property_id="FARM-RF002",
        reporting_period="2026-03",
        original_filename="entrada.csv",
    )
    assert meta.get("artifact_id")
    stored = Path(meta["stored_path"]).resolve()
    assert str(agrotrace_data_root.resolve()) in str(stored)

    cycle_id = "CYCLE-RF002-ADAPTER"
    save_cycle({
        "cycle_id": cycle_id,
        "property_id": "FARM-RF002",
        "reporting_period": "2026-03",
        "raw_file": meta,
    })

    retrieved = save_file_adapter.retrieve_by_cycle_id(cycle_id)
    assert retrieved["content"] == payload
    assert retrieved["cycle_id"] == cycle_id
    assert retrieved["artifact_id"] == meta["artifact_id"]
    assert retrieved["registered_sha256"] == retrieved["recomputed_sha256"]
    assert retrieved["verification_status"] == "verified"

    dto = save_file_adapter.to_ui_dto(retrieved)
    assert "stored_path" not in dto
    assert "content" not in dto
    assert dto["original_filename"] == "entrada.csv"
    assert dto["cycle_id"] == cycle_id


def test_adapter_retrieve_original_by_artifact_id(agrotrace_data_root: Path) -> None:
    payload = b"direct-artifact-lookup\n"
    meta = save_file_adapter.save_uploaded_content(
        payload,
        property_id="FARM-RF002",
        reporting_period="2026-04",
        original_filename="direct.csv",
    )
    retrieved = save_file_adapter.retrieve_original(artifact_id=meta["artifact_id"])
    assert retrieved["content"] == payload
    assert Path(str(agrotrace_data_root / "save_file" / "originals")).exists()


def test_adapter_artifact_not_found(agrotrace_data_root: Path) -> None:
    with pytest.raises(save_file_adapter.ArtifactNotFoundError):
        save_file_adapter.retrieve_original(
            artifact_id="11111111-1111-1111-1111-111111111111"
        )
