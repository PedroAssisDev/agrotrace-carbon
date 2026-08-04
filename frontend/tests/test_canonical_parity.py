"""Parity: frontend official hash == blockchain-service json_canonical_v1."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BC = REPO / "agrotrace-carbon-blockchain-service"
FRONT = REPO / "frontend"
VECTORS = BC / "schemas" / "canonical" / "canonical_vectors.json"

sys.path.insert(0, str(BC))
sys.path.insert(0, str(FRONT))


def test_no_compact_fallback_in_sha256_dict_source() -> None:
    src = (FRONT / "utils" / "hash_helpers.py").read_text(encoding="utf-8")
    assert "Falls back to a local compact JSON" not in src
    assert "CanonicalizationUnavailableError" in src
    assert "def ui_preview_hash" in src


def test_frontend_matches_blockchain_vectors() -> None:
    from app.domain.services.canonical_json_service import to_canonical_json
    from app.domain.services.sha256_service import sha256_hex
    from services import direct_imports as di
    from utils.hash_helpers import official_package_hash, sha256_dict

    assert di.sha256_hex is not None, "blockchain-service must be importable for official hash"
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    for entry in data["vectors"]:
        if "payloads" not in entry or not entry.get("expect_equal_bytes", True):
            continue
        if entry["id"] in {"value_alteration_diverges", "list_order_matters", "unknown_method_raises"}:
            continue
        payload = entry["payloads"][0]
        assert to_canonical_json(payload) == entry.get("canonical_bytes") or entry.get("canonical_bytes") is None
        official = sha256_hex(payload)
        assert sha256_dict(payload) == official
        assert official_package_hash(payload) == official
        if "hash" in entry:
            assert official == entry["hash"]


def test_sha256_dict_fails_closed_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import direct_imports as di
    from utils.hash_helpers import CanonicalizationUnavailableError, sha256_dict

    monkeypatch.setattr(di, "sha256_hex", None)
    with pytest.raises(CanonicalizationUnavailableError):
        sha256_dict({"a": 1})
