"""Testes RNF010 — VersionManifest + ABI versionada."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.mock_data import mock_full_cycle
from services.version_manifest_service import (
    VersionManifest,
    assert_consistent,
    attach_version_manifest,
    build_version_manifest,
    evidence_metadata_summary,
)
from services.audit_payload_service import resolve_payload


def test_version_manifest_complete_from_mock_cycle(agrotrace_data_root: Path):
    from services import bootstrap

    bootstrap.configure_paths()
    cycle = mock_full_cycle()
    cycle.setdefault("calculation", {})["method"] = {
        "code": "ECOFARM-T1-DAIRY",
        "version": "1.0.0",
    }
    cycle["calculation"]["gwp"] = {"CH4": 25.0, "N2O": 298.0, "source": "ipcc_ar4"}
    cycle["wrapper"] = {"layout_id": "monthly:v1", "layout_version": "v1"}
    cycle["layout_id"] = "monthly:v1"
    cycle["ontology"] = {"ontology_version": "agromrv_lite_v2026_01", "ontology_name": "AgroMRV-Lite"}

    mf = build_version_manifest(
        cycle,
        network_meta={
            "contract_name": "CarbonEvidenceRegistry",
            "contract_version": "1.0.0",
            "abi_checksum_sha256": "abc",
            "chain_id": 11155111,
            "contract_address": "",
        },
    )
    d = mf.to_dict()
    assert d["layout_id"]["value"] == "monthly:v1"
    assert d["method_code"]["value"] == "ECOFARM-T1-DAIRY"
    assert d["canonicalization_strategy"]["value"] == "json_canonical_v1"
    assert d["manifest_hash"]


def test_version_manifest_missing_field_has_reason():
    cycle = {"cycle_id": "c1"}
    mf = build_version_manifest(cycle)
    d = mf.to_dict()
    assert d["prediction_model_id"]["value"] is None
    assert d["prediction_model_id"]["missing_reason"] == "not_applicable"
    assert d["layout_id"]["missing_reason"]


def test_version_manifest_conflict_detection():
    cycle = {
        "cycle_id": "c1",
        "layout_id": "monthly:v1",
        "wrapper": {"layout_id": "monthly:v1"},
        "ontology": {"ontology_version": "vA"},
        "calculation": {"method": {"code": "M1", "version": "1.0.0"}},
    }
    mf = build_version_manifest(cycle)
    # Force contradiction
    mf.ontology_version.value = "vB"
    conflicts = assert_consistent(mf, cycle)
    assert any("ontology_version" in c for c in conflicts)


def test_version_manifest_serialization_roundtrip():
    cycle = mock_full_cycle()
    mf = build_version_manifest(cycle)
    restored = VersionManifest.from_dict(mf.to_dict())
    assert restored.to_dict()["cycle_id"] == mf.cycle_id
    assert restored.to_dict()["contract_version"] == mf.contract_version


def test_version_manifest_in_package_metadata_and_audit(agrotrace_data_root: Path):
    from services import bootstrap

    bootstrap.configure_paths()
    cycle = mock_full_cycle()
    data = attach_version_manifest(cycle)
    assert cycle["version_manifest"]["manifest_hash"]
    summary = evidence_metadata_summary(data)
    assert "version_manifest_ref" in summary
    assert summary["canonicalization_strategy"] == "json_canonical_v1"

    payload = resolve_payload("version_manifest", cycle)
    assert payload["source"] == "version_manifest"
    assert payload["data"] is not None
    blob = str(payload["data"])
    assert "private_key" not in blob.lower() or "********" in blob


def test_abi_versioned_load_and_checksum():
    import sys

    root = Path(__file__).resolve().parents[2] / "agrotrace-carbon-blockchain-service"
    sys.path.insert(0, str(root))
    from app.infrastructure.anchoring.abi_versioning import (
        AbiVersionError,
        abi_checksum_sha256,
        resolve_abi_path,
        validate_abi_file,
    )

    path = resolve_abi_path(contract_version="1.0.0")
    assert path.name == "CarbonEvidenceRegistry.abi.v1.0.0.json"
    meta = validate_abi_file(path, expected_version="1.0.0")
    assert meta["entry_count"] > 0
    checksum = abi_checksum_sha256(path)
    assert len(checksum) == 64

    with pytest.raises(AbiVersionError):
        validate_abi_file(path, expected_version="9.9.9")

    with pytest.raises(AbiVersionError):
        validate_abi_file(path, expected_checksum="0" * 64)

    legacy = resolve_abi_path(contract_version=None)
    assert legacy.exists()
