"""Resolução de nomes de CSV de exemplo."""

from __future__ import annotations

from pathlib import Path

INTRADAY_CSV_NAMES = ("intraday_report.csv", "pesoXleite_parsed.csv")
MONTHLY_CSV_NAMES = ("monthly_report.csv", "validate_data_mensal.csv")
ANNUAL_CSV_NAMES = ("annual_report.csv", "validated_data_anual.csv")


def resolve_csv(data_dir: Path, candidates: tuple[str, ...]) -> Path | None:
    for name in candidates:
        p = data_dir / name
        if p.is_file():
            return p
    return None
