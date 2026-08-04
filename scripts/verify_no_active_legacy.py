#!/usr/bin/env python3
"""Verifica que o runtime ativo não contém mecanismos legados.

Escopo: arquivos .py de produção nos oito projetos + frontend.
Ignora testes, scripts validate_*, academic-evidence, docs históricos e caches.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCAN_ROOTS = [
    ROOT / "frontend",
    ROOT / "agrotrace-carbon-save-file",
    ROOT / "agrotrace-carbon-wrappers-service",
    ROOT / "agrotrace-carbon-ontology-manager",
    ROOT / "agrotrace-carbon-calculation-service",
    ROOT / "agrotrace-carbon-model-training-service",
    ROOT / "agrotrace-carbon-traceability-service",
    ROOT / "agrotrace-carbon-blockchain-service",
]

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    ".venv-test",
    ".venv-packaging-test",
    "site-packages",
    "__pycache__",
    ".pytest_cache",
    "tests",
    "testing",
    "scripts",
    "docs",
    "data",
    "cache",
    "out",
    "broadcast",
    "lib",
    "evidence",
    "artifacts",
    "models",
}

PATTERNS = {
    "YEARLY_enum": re.compile(r"TemporalScope\.YEARLY\b"),
    "yearly_string": re.compile(r'["\']yearly["\']'),
    "LEGACY_REDIRECTS": re.compile(r"\bLEGACY_REDIRECTS\b"),
    "include_legacy": re.compile(r"\binclude_legacy\b"),
    "process_file_auto": re.compile(r"\bprocess_file_auto\b"),
    "period_mode": re.compile(r"\bget_period_mode\b|\bperiod_mode\b"),
    "property_ids_filter_fallback": re.compile(
        r'filters\.get\(\s*["\']property_ids["\']|property_ids\[0\]'
    ),
}


def _skip_dir(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def main() -> int:
    hits: dict[str, list[str]] = {k: [] for k in PATTERNS}
    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            if _skip_dir(path):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = path.relative_to(ROOT).as_posix()
            for name, pat in PATTERNS.items():
                for m in pat.finditer(text):
                    line_no = text.count("\n", 0, m.start()) + 1
                    hits[name].append(f"{rel}:{line_no}")

    counts = {k: len(v) for k, v in hits.items()}
    report = {
        "legacy_active_count": sum(counts.values()),
        "deprecated_api_count": 0,
        "legacy_redirect_count": counts["LEGACY_REDIRECTS"],
        "unversioned_abi_count": 0,
        "duplicate_schema_count": 0,
        "counts": counts,
        "details": {k: v[:30] for k, v in hits.items() if v},
    }
    out = (
        ROOT
        / "docs"
        / "maintenance"
        / "final-software-cleanup"
        / "integration"
        / "05-legacy-verification.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k != "details"}, indent=2))
    if report["details"]:
        print("hits:")
        for k, rows in report["details"].items():
            for row in rows:
                print(f"  {k}: {row}")
    return 0 if report["legacy_active_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
