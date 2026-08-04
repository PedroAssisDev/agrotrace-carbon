"""Testes RF002 — retrieve_original (round-trip, erros de domínio)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from save_file.errors import (
    ArtifactNotFoundError,
    IntegrityMismatchError,
    MetadataNotFoundError,
    StoragePathEscapeError,
)
from save_file.hashing import sha256_bytes
from save_file.storage import retrieve_original, save_original_content


class RetrieveOriginalTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "originals"
        self.root.mkdir(parents=True, exist_ok=True)
        self.payload = b"col_a,col_b\n1,2\nlinha-exata-rf002\n"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_save_retrieve_bytes_equal(self) -> None:
        meta = save_original_content(
            self.payload,
            property_id="FARM-001",
            reporting_period="2026-01",
            original_filename="sample.csv",
            dest_dir=self.root,
        )
        retrieved = retrieve_original(artifact_id=meta["artifact_id"], dest_dir=self.root)
        self.assertEqual(retrieved.content, self.payload)
        self.assertEqual(retrieved.original_filename, "sample.csv")
        self.assertEqual(retrieved.verification_status, "verified")

    def test_hashes_match(self) -> None:
        meta = save_original_content(
            self.payload,
            property_id="FARM-001",
            reporting_period="2026-01",
            original_filename="sample.csv",
            dest_dir=self.root,
        )
        retrieved = retrieve_original(artifact_id=meta["artifact_id"], dest_dir=self.root)
        expected = sha256_bytes(self.payload)
        self.assertEqual(meta["sha256"], expected)
        self.assertEqual(retrieved.registered_sha256, expected)
        self.assertEqual(retrieved.recomputed_sha256, expected)

    def test_artifact_not_found(self) -> None:
        with self.assertRaises(ArtifactNotFoundError):
            retrieve_original(artifact_id="00000000-0000-0000-0000-000000000000", dest_dir=self.root)

    def test_metadata_not_found(self) -> None:
        meta = save_original_content(
            self.payload,
            property_id="FARM-001",
            reporting_period="2026-01",
            original_filename="sample.csv",
            dest_dir=self.root,
        )
        stored = Path(meta["stored_path"])
        bare = self.root / "orphan_no_meta.csv"
        bare.write_bytes(self.payload)
        meta_path = stored.with_suffix(stored.suffix + ".meta.json")
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        data["stored_path"] = str(bare)
        meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        with self.assertRaises(MetadataNotFoundError):
            retrieve_original(artifact_id=meta["artifact_id"], dest_dir=self.root)

    def test_path_traversal_rejected(self) -> None:
        meta = save_original_content(
            self.payload,
            property_id="FARM-001",
            reporting_period="2026-01",
            original_filename="sample.csv",
            dest_dir=self.root,
        )
        stored = Path(meta["stored_path"])
        meta_path = stored.with_suffix(stored.suffix + ".meta.json")
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        outside = Path(self._tmp.name) / "outside_escape.csv"
        outside.write_bytes(self.payload)
        data["stored_path"] = str(outside)
        meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        with self.assertRaises(StoragePathEscapeError):
            retrieve_original(artifact_id=meta["artifact_id"], dest_dir=self.root)

    def test_integrity_mismatch_after_tamper(self) -> None:
        meta = save_original_content(
            self.payload,
            property_id="FARM-001",
            reporting_period="2026-01",
            original_filename="sample.csv",
            dest_dir=self.root,
        )
        stored = Path(meta["stored_path"])
        stored.write_bytes(self.payload + b"\nTAMPER")

        with self.assertRaises(IntegrityMismatchError) as ctx:
            retrieve_original(artifact_id=meta["artifact_id"], dest_dir=self.root)
        self.assertEqual(ctx.exception.registered_sha256, meta["sha256"])
        self.assertNotEqual(ctx.exception.recomputed_sha256, meta["sha256"])

    def test_legacy_retrieve_by_sha256(self) -> None:
        """Artefatos sem artifact_id (legado) recuperáveis por sha256."""
        meta = save_original_content(
            self.payload,
            property_id="FARM-LEGACY",
            reporting_period="2025-12",
            original_filename="legacy.csv",
            dest_dir=self.root,
        )
        stored = Path(meta["stored_path"])
        meta_path = stored.with_suffix(stored.suffix + ".meta.json")
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        data.pop("artifact_id", None)
        meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        retrieved = retrieve_original(sha256=meta["sha256"], dest_dir=self.root)
        self.assertEqual(retrieved.content, self.payload)
        self.assertIsNone(retrieved.artifact_id)


if __name__ == "__main__":
    unittest.main()
