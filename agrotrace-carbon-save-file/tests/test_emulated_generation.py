"""Testes unitários da geração emulada."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from save_file.emulated import (
    expected_approval_count,
    expected_entry_count,
    generate_emulated_uploads,
    validate_emulated_directory,
)
from save_file.emulated.generators.monthly import MONTHLY_HEADER


class EmulatedGenerationTests(unittest.TestCase):
    def test_demo_counts(self) -> None:
        # Diário desativado: 12 mensais + 5 anuais = 17 entradas / 17 ciclos
        self.assertEqual(expected_entry_count("demo"), 17)
        self.assertEqual(expected_approval_count("demo"), 17)

    def test_reproducible_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "a"
            out.mkdir()
            r1 = generate_emulated_uploads(global_seed=42, profile_mode="demo", output_dir=out, wipe=True)
            manifest1 = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            sample = next(out.glob("emulated_*_monthly_2026-01.csv"))
            text1 = sample.read_text(encoding="utf-8")

            out2 = Path(tmp) / "b"
            out2.mkdir()
            generate_emulated_uploads(global_seed=42, profile_mode="demo", output_dir=out2, wipe=True)
            manifest2 = json.loads((out2 / "manifest.json").read_text(encoding="utf-8"))
            sample2 = next(out2.glob("emulated_*_monthly_2026-01.csv"))
            text2 = sample2.read_text(encoding="utf-8")

        self.assertEqual(manifest1, manifest2)
        self.assertEqual(text1, text2)
        self.assertEqual(len(r1["paths"]), 17)

    def test_no_emission_columns_in_monthly(self) -> None:
        self.assertNotIn("ef_enteric_kgCH4", MONTHLY_HEADER)
        self.assertNotIn("enteric_tCO2e", MONTHLY_HEADER)

    def test_validate_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            generate_emulated_uploads(global_seed=7, profile_mode="demo", output_dir=out, wipe=True)
            errors = validate_emulated_directory(out)
            self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
