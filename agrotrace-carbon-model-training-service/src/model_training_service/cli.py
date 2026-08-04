from __future__ import annotations

import argparse
import json
from pathlib import Path

from model_training_service.api.facade import ModelTrainingFacade
from model_training_service.config import load_config
from model_training_service.data.csv_source import CsvApprovedResultsSource
from model_training_service.data.sparql_source import SparqlApprovedResultsSource


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Treinamento de modelos do CarbonSECO")
    subparsers = parser.add_subparsers(dest="command", required=True)
    train = subparsers.add_parser("train-all", help="Gera todos os modelos habilitados")
    source = train.add_mutually_exclusive_group(required=False)
    source.add_argument("--csv", help="CSV com resultados aprovados")
    source.add_argument("--sparql-endpoint", help="Endpoint SPARQL da ontologia")
    train.add_argument("--sparql-query", help="Arquivo de consulta SPARQL")
    train.add_argument("--separator", help="Separador do CSV; autodetectado quando omitido")
    train.add_argument("--config", default="configs/training.yaml")
    train.add_argument(
        "--report",
        default=None,
        help="Caminho do relatório JSON (padrão: <artifacts_dir>/last_training_report.json)",
    )
    return parser


def build_data_source(args: argparse.Namespace) -> dict | None:
    if args.csv:
        location = Path(args.csv).expanduser().resolve()
        return {"type": "csv", "location": str(location), "path": str(location)}
    if args.sparql_endpoint:
        if not args.sparql_query:
            raise SystemExit("--sparql-query é obrigatório quando --sparql-endpoint é usado.")
        query_path = Path(args.sparql_query).expanduser().resolve()
        return {
            "type": "sparql",
            "endpoint": str(args.sparql_endpoint),
            "query_file": str(query_path),
        }
    return None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(Path(args.config).expanduser().resolve())
    override = build_data_source(args)
    facade = ModelTrainingFacade(config=config, background=False)

    if override and override.get("type") == "csv":
        source = CsvApprovedResultsSource(
            Path(override["location"]), separator=args.separator
        )
        report = facade.train_all_sync(source.load(), data_source=override)
    elif override and override.get("type") == "sparql":
        source = SparqlApprovedResultsSource(
            override["endpoint"], override["query_file"]
        )
        report = facade.train_all_sync(source.load(), data_source=override)
    else:
        report = facade.train_all_sync()

    if args.report:
        report_path = Path(args.report).expanduser().resolve()
    else:
        report_path = Path(config["paths"]["artifacts_dir"]) / "last_training_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_json = json.dumps(report, indent=2, ensure_ascii=False)
    report_path.write_text(report_json, encoding="utf-8")
    try:
        print(report_json)
    except UnicodeEncodeError:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    return 1 if report.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
