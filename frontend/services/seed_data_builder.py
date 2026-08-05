"""Gera CSVs determinísticos para o seed de ciclos pendentes.

DEPRECATED: use save_file.emulated (generate_emulated_uploads) + emulated_import_service.
Este módulo delega ao gerador emulado para compatibilidade retroativa.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Any

import config

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
SAVE_FILE_ROOT = config.SAVE_FILE_SERVICE_DIR
if str(SAVE_FILE_ROOT) not in sys.path:
    sys.path.insert(0, str(SAVE_FILE_ROOT))

from save_file.emulated.planner import expected_approval_count, expected_entry_count  # noqa: E402
from save_file.emulated.writer import generate_emulated_uploads  # noqa: E402

# Manifesto deprecated fica junto dos uploads emulados (destino real da geração)
SEED_DIR = config.SAVE_FILE_EMULATED_UPLOADS_DIR
MANIFEST_PATH = SEED_DIR / "manifest.json"


def ensure_seed_dir() -> Path:
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    return SEED_DIR


def build_all_seed_files(
    *,
    global_seed: int = 42,
    profile_mode: str = "demo",
) -> dict[str, Any]:
    """Delega geração ao pacote emulated (staging em save-file)."""
    warnings.warn(
        "seed_data_builder.build_all_seed_files está deprecated; "
        "use save_file.emulated.generate_emulated_uploads",
        DeprecationWarning,
        stacklevel=2,
    )
    out = config.SAVE_FILE_EMULATED_UPLOADS_DIR
    result = generate_emulated_uploads(
        global_seed=global_seed,
        profile_mode=profile_mode,
        output_dir=out,
        wipe=True,
    )
    manifest = result["manifest"].to_dict()
    ensure_seed_dir()
    MANIFEST_PATH.write_text(
        __import__("json").dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "manifest_path": MANIFEST_PATH,
        "manifest": manifest,
        "paths": result["paths"],
        "plans": result.get("planned_groups"),
    }


__all__ = [
    "MANIFEST_PATH",
    "SEED_DIR",
    "build_all_seed_files",
    "ensure_seed_dir",
    "expected_approval_count",
    "expected_entry_count",
]
