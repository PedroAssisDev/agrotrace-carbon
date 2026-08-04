from pathlib import Path

from model_training_service.cli import build_data_source, build_parser


def test_build_data_source_csv_resolves_absolute(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "data" / "approved.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text("property_id\n", encoding="utf-8")
    other = tmp_path / "elsewhere"
    other.mkdir()
    monkeypatch.chdir(other)

    parser = build_parser()
    args = parser.parse_args(
        ["train-all", "--csv", str(Path("..") / "data" / "approved.csv"), "--config", "x.yaml"]
    )
    # Relative to CWD (elsewhere): ../data/approved.csv
    relative = Path("..") / "data" / "approved.csv"
    args.csv = str(relative)
    source = build_data_source(args)
    assert source["type"] == "csv"
    assert Path(source["location"]).is_absolute()
    assert Path(source["location"]) == csv_path.resolve()


def test_build_data_source_sparql_resolves_query(tmp_path: Path):
    query = tmp_path / "query.rq"
    query.write_text("SELECT * WHERE {}", encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(
        [
            "train-all",
            "--sparql-endpoint",
            "http://example.org/sparql",
            "--sparql-query",
            str(query),
            "--config",
            "x.yaml",
        ]
    )
    source = build_data_source(args)
    assert source == {
        "type": "sparql",
        "endpoint": "http://example.org/sparql",
        "query_file": str(query.resolve()),
    }
