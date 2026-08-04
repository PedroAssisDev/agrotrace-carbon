"""Validação de CSVs emulados (headers e ausência de emissões pré-calculadas)."""

from __future__ import annotations

import csv
from pathlib import Path

from save_file.emulated.generators.annual import ANNUAL_HEADER
from save_file.emulated.generators.monthly import MONTHLY_HEADER

FORBIDDEN_MONTHLY = {"ef_enteric_kgCH4", "enteric_tCO2e", "ef_enteric_kg_ch4"}


def validate_monthly_file(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter=";")
        header = next(reader, None)
    if not header:
        return ["header vazio"]
    forbidden = FORBIDDEN_MONTHLY & {h.strip() for h in header}
    if forbidden:
        errors.append(f"colunas de emissão proibidas: {sorted(forbidden)}")
    expected = MONTHLY_HEADER
    if header != expected:
        errors.append(f"header mensal diverge (esperado {len(expected)} cols, obteve {len(header)})")
    return errors


def validate_annual_file(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter=";")
        header = next(reader, None)
    if not header:
        return ["header vazio"]
    if header != ANNUAL_HEADER:
        errors.append(f"header anual diverge (esperado {len(ANNUAL_HEADER)}, obteve {len(header)})")
    return errors


def validate_intraday_file(path: Path) -> list[str]:
    errors: list[str] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh, delimiter=",")
        header = next(reader, None)
        rows = list(reader)
    if header != ["Date", "Tag", "Milk", "Weight"]:
        errors.append(f"header intraday inválido: {header}")
    if len(rows) < 5:
        errors.append(f"poucas linhas intraday: {len(rows)}")
    return errors


def validate_emulated_directory(directory: Path) -> list[str]:
    errors: list[str] = []
    manifest = directory / "manifest.json"
    if not manifest.exists():
        return [f"manifest ausente: {manifest}"]
    for path in sorted(directory.glob("emulated_*.csv")):
        name = path.name.lower()
        if "_monthly_" in name:
            errors.extend(f"{path.name}: {e}" for e in validate_monthly_file(path))
        elif "_annual_" in name:
            errors.extend(f"{path.name}: {e}" for e in validate_annual_file(path))
        elif "_intraday_" in name:
            errors.extend(f"{path.name}: {e}" for e in validate_intraday_file(path))
    return errors
