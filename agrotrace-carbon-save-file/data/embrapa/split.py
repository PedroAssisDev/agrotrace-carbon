"""Split Embrapa annual/monthly/daily CSVs by key columns and save one file per group."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

SOURCES = (
    {
        "input": BASE_DIR / "annual_report.csv",
        "output_dir": BASE_DIR / "annual",
        "columns": ("Property_Name",),
        "sep": ";",
    },
    {
        "input": BASE_DIR / "monthly_report.csv",
        "output_dir": BASE_DIR / "monthly",
        "columns": ("Property", "Period"),
        "sep": ";",
    },
    {
        "input": BASE_DIR / "daily_report.csv",
        "output_dir": BASE_DIR / "daily",
        "columns": ("Date",),
        "sep": ",",
    },
)


def _sanitize_for_filename(value: object) -> str:
    text = str(value).strip()
    text = re.sub(r"[^\w\-]+", "_", text, flags=re.UNICODE)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def _group_suffix(key: object, columns: tuple[str, ...]) -> str:
    values = key if isinstance(key, tuple) else (key,)
    parts = [_sanitize_for_filename(value) for value in values]
    return "_".join(parts)


def split_csv(
    input_path: Path,
    output_dir: Path,
    columns: tuple[str, ...],
    *,
    sep: str = ";",
) -> int:
    if not input_path.is_file():
        raise FileNotFoundError(f"Arquivo nao encontrado: {input_path}")

    df = pd.read_csv(input_path, sep=sep, dtype=str)
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise KeyError(
            f"Coluna(s) {missing} ausente(s) em {input_path.name}: {list(df.columns)}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    for old_file in output_dir.glob(f"{input_path.stem}_*.csv"):
        old_file.unlink()

    stem = input_path.stem
    written = 0

    for key, group in df.groupby(list(columns), dropna=False, sort=False):
        suffix = _group_suffix(key, columns)
        out_path = output_dir / f"{stem}_{suffix}.csv"
        group.to_csv(out_path, sep=sep, index=False)
        written += 1
        print(f"  {out_path.name} ({len(group)} linhas)")

    return written


def main() -> None:
    total = 0
    for source in SOURCES:
        cols = ", ".join(source["columns"])
        print(f"\n{source['input'].name} -> {source['output_dir'].name}/ (por {cols})")
        total += split_csv(
            source["input"],
            source["output_dir"],
            source["columns"],
            sep=str(source.get("sep", ";")),
        )
    print(f"\nConcluido: {total} arquivos gerados.")


if __name__ == "__main__":
    main()
