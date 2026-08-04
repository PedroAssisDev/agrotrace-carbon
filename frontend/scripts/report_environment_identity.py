#!/usr/bin/env python
"""Snapshot não destrutivo da identidade do ambiente / versão do código.

Produz: data/hora, branch, commit SHA (se Git), versões Python/deps,
contagem de artefatos antes e depois (deve ser idêntica), caminhos relativos
dos bancos. Não imprime segredos.

Uso:
    cd frontend
    python scripts/report_environment_identity.py
    python scripts/report_environment_identity.py --data-root C:/tmp/isolated
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = FRONTEND_ROOT.parent
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

import config  # noqa: E402
from utils.data_root_cli import apply_data_root_from_argv  # noqa: E402

apply_data_root_from_argv()

_DEP_PACKAGES = (
    "dash",
    "dash-bootstrap-components",
    "plotly",
    "pandas",
    "numpy",
    "sqlalchemy",
    "owlready2",
    "joblib",
)


def _git(*args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def _pkg_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not-installed"


def _count_artifacts() -> dict[str, int]:
    def _files(directory: Path, pattern: str = "*") -> int:
        if not directory.exists():
            return 0
        return sum(1 for p in directory.glob(pattern) if p.is_file() and p.name != ".gitkeep")

    return {
        "cycles": _files(config.CYCLES_DIR, "*.json"),
        "normalized": _files(config.NORMALIZED_DIR),
        "ontology_exports": _files(config.ONTOLOGY_EXPORTS_DIR),
        "publications": _files(config.PUBLICATIONS_DIR, "*.json"),
        "evidence_packages": _files(config.EVIDENCE_PACKAGES_DIR, "*.json"),
        "properties": _files(config.PROPERTIES_DIR, "*.json"),
        "logs": _files(config.LOGS_DIR),
        "save_file_originals": _files(config.SAVE_FILE_ORIGINALS_DIR),
        "provenance_db_present": 1 if config.PROV_DB_PATH.exists() else 0,
        "blockchain_db_present": 1 if config.BLOCKCHAIN_DB_PATH.exists() else 0,
    }


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(WORKSPACE_ROOT.resolve()).as_posix()
    except ValueError:
        try:
            return path.resolve().relative_to(config.DATA_DIR.resolve()).as_posix()
        except ValueError:
            return path.name


def build_report() -> dict[str, Any]:
    counts_before = _count_artifacts()
    # Operação não destrutiva: apenas releitura
    counts_after = _count_artifacts()

    git_dir = WORKSPACE_ROOT / ".git"
    git_available = git_dir.exists()
    branch = _git("branch", "--show-current") or _git("symbolic-ref", "--short", "HEAD")
    sha = _git("rev-parse", "HEAD")
    if git_available and not branch:
        branch = "master (sem commits)"
    if git_available and not sha:
        sha = "unavailable (sem commits)"

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "git": {
            "available": git_available,
            "branch": branch or "unavailable",
            "commit_sha": sha or "unavailable",
        },
        "dependencies": {name: _pkg_version(name) for name in _DEP_PACKAGES},
        "data_root": {
            "path": str(config.DATA_DIR),
            "custom": config.is_custom_data_root(),
            "relative_to_workspace": _rel(config.DATA_DIR),
        },
        "databases_relative": {
            "provenance": _rel(config.PROV_DB_PATH),
            "blockchain": _rel(config.BLOCKCHAIN_DB_PATH),
        },
        "artifact_counts_before": counts_before,
        "artifact_counts_after": counts_after,
        "counts_unchanged": counts_before == counts_after,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["counts_unchanged"]:
        print("AVISO: contagens antes/depois divergiram (inesperado).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
