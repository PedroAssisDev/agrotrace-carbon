"""Build AgroMRV-O Lite ontology and populate from processed normalized CSVs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from ontology import build_full_ontology, export_ontology, populate_from_csv
from ontology.population import DEFAULT_DELIM
from ontology.validators import validate_all

REPO_ROOT = Path(__file__).resolve().parent

LAYOUTS = {
    "annual": {"family": "annual", "layout_name": "annual_inventory"},
    "intraday": {"family": "intraday", "layout_name": "daily_production"},
    "monthly": {"family": "monthly", "layout_name": "monthly_property"},
}

DEFAULT_DATA_DIR = REPO_ROOT.parent / "data" / "processed"
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "ontology" / "agromrv_lite.owl"

POPULATION_ORDER = ("annual", "intraday", "monthly")


def find_latest_normalized(data_dir: Path, family: str) -> Path:
    """Return the most recent *_normalized.delimited.csv for a data family."""
    pattern = f"{family}/**/*_normalized.delimited.csv"
    matches = list(data_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(
            f"No normalized CSV found for family '{family}' under {data_dir} (pattern: {pattern})"
        )
    return max(matches, key=lambda path: path.stat().st_mtime)


def resolve_inputs(
    data_dir: Path,
    overrides: dict[str, Path | None],
) -> dict[str, Path]:
    """Resolve annual, intraday, and monthly input CSV paths."""
    resolved: dict[str, Path] = {}
    for key in POPULATION_ORDER:
        override = overrides.get(key)
        if override is not None:
            path = override.resolve()
            if not path.is_file():
                raise FileNotFoundError(f"Override CSV not found for {key}: {path}")
            resolved[key] = path
            continue
        resolved[key] = find_latest_normalized(data_dir, LAYOUTS[key]["family"])
    return resolved


def count_csv_rows(csv_path: Path) -> int:
    df = pd.read_csv(
        csv_path, sep=DEFAULT_DELIM, engine="python", dtype=str, keep_default_na=False
    )
    return len(df)


def run_pipeline(
    inputs: dict[str, Path],
    output_path: Path,
    *,
    validate: bool = False,
    export_ttl: bool = False,
) -> None:
    """Build ontology, populate from all inputs, optionally validate, and export."""
    onto = build_full_ontology()

    for key in POPULATION_ORDER:
        path = inputs[key]
        layout_name = LAYOUTS[key]["layout_name"]
        row_count = count_csv_rows(path)
        print(f"Populating {key} ({row_count} rows) from {path.name} [{layout_name}]")
        populate_from_csv(
            onto,
            str(path),
            layout_name=layout_name,
            source_name=path.name,
        )

    if validate:
        issues = validate_all(onto, include_instances=True)
        if issues:
            print("Validation failed:", file=sys.stderr)
            for issue in issues:
                print(f"  - {issue}", file=sys.stderr)
            raise SystemExit(1)
        print("Validation passed")

    output_path = output_path.resolve()
    export_ontology(onto, str(output_path), format="rdfxml")
    print(f"Exported ontology to {output_path}")

    if export_ttl:
        ttl_path = output_path.with_suffix(".ttl")
        export_ontology(onto, str(ttl_path), format="turtle")
        print(f"Exported ontology to {ttl_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and populate AgroMRV-O Lite from processed normalized CSVs."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Directory with processed data (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output .owl path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--annual-csv",
        type=Path,
        default=None,
        help="Override path for annual normalized CSV",
    )
    parser.add_argument(
        "--intraday-csv",
        type=Path,
        default=None,
        help="Override path for intraday normalized CSV",
    )
    parser.add_argument(
        "--monthly-csv",
        type=Path,
        default=None,
        help="Override path for monthly normalized CSV",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run ontology validation before export; exit 1 on failure",
    )
    parser.add_argument(
        "--export-ttl",
        action="store_true",
        help="Also export Turtle (.ttl) alongside the .owl file",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    data_dir = args.data_dir.resolve()
    if not data_dir.is_dir():
        raise SystemExit(f"Data directory not found: {data_dir}")

    overrides = {
        "annual": args.annual_csv,
        "intraday": args.intraday_csv,
        "monthly": args.monthly_csv,
    }
    inputs = resolve_inputs(data_dir, overrides)

    print(f"Data directory: {data_dir}")
    for key in POPULATION_ORDER:
        print(f"  {key}: {inputs[key]}")

    run_pipeline(
        inputs,
        args.output,
        validate=args.validate,
        export_ttl=args.export_ttl,
    )


if __name__ == "__main__":
    main()
