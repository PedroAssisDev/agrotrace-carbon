#!/usr/bin/env python3
"""Gera software-release/ limpo (sem academic-evidence, bancos ou caches)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "software-release"

INCLUDE = [
    "README.md",
    "LICENSE",
    "ecosystem-manifest.json",
    ".env.example",
    ".gitignore",
    "agrotrace-carbon.code-workspace",
    "docs",
    "scripts",
    "logo",
    "frontend",
    "agrotrace-carbon-save-file",
    "agrotrace-carbon-wrappers-service",
    "agrotrace-carbon-ontology-manager",
    "agrotrace-carbon-calculation-service",
    "agrotrace-carbon-model-training-service",
    "agrotrace-carbon-traceability-service",
    "agrotrace-carbon-blockchain-service",
]

EXCLUDE_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    ".venv-test",
    ".venv-packaging-test",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "data",
    "evidence",
    "artifacts",
    "models",
    "cache",
    "out",
    "broadcast",
    "htmlcov",
    "dist",
    "build",
    "academic-evidence",
    "software-release",
    "docs/archive",
    "docs/audits/archive",
    "docs/maintenance/project-reorganization",
}


def _ignored(src: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name in EXCLUDE_DIR_NAMES or name.endswith(".egg-info"):
            ignored.add(name)
        if name.endswith((".db", ".sqlite", "-wal", "-shm")):
            ignored.add(name)
        if name == ".env":
            ignored.add(name)
    return ignored


def main() -> int:
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    for item in INCLUDE:
        src = ROOT / item
        if not src.exists():
            print(f"skip missing: {item}")
            continue
        dst = DEST / item
        if src.is_dir():
            shutil.copytree(src, dst, ignore=_ignored)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    # Marker
    (DEST / "RELEASE_NOTES.md").write_text(
        "# AgroTrace Carbon — software-release 1.0.0\n\n"
        "Pacote executável limpo. Não depende de academic-evidence/.\n"
        "Instalação: `scripts/install-workspace.ps1` ou `.sh`.\n",
        encoding="utf-8",
    )
    print(f"software-release written to {DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
