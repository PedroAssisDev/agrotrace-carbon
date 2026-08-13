"""Discover dos CSVs diários Embrapa (sem rodar a pipeline)."""

from __future__ import annotations

from pathlib import Path

from services.embrapa_import_service import _discover_daily


def test_discover_daily_groups_by_month(tmp_path: Path) -> None:
    for name, date in (
        ("daily_report_2021-01-31.csv", "2021-01-31"),
        ("daily_report_2021-02-28.csv", "2021-02-28"),
    ):
        (tmp_path / name).write_text(
            f"Date,Tag,Milk,Weight\n{date},2195,47.8,643.0\n",
            encoding="utf-8",
        )

    items = _discover_daily(tmp_path)
    assert [i["cycle_id"] for i in items] == [
        "EMBRAPA-D-1-2021-01",
        "EMBRAPA-D-1-2021-02",
    ]
    assert items[0]["reporting_period"] == "2021-01"
    assert items[0]["payloads"][0]["reporting_period"] == "2021-01-31"
    assert items[0]["payloads"][0]["original_filename"] == "daily_report_2021-01-31.csv"
    assert "1 dia(s)" in items[0]["coverage_label"]


def test_discover_daily_missing_dir(tmp_path: Path) -> None:
    assert _discover_daily(tmp_path / "missing") == []
