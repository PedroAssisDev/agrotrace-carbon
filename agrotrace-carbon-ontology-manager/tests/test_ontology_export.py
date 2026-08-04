"""Tests for ontology export."""

from pathlib import Path

from ontology.examples import ANNUAL_CSV
from ontology.exporters import export_ontology
from ontology.population import populate_from_dataframe, read_dataframe_from_csv_string


def test_export_ontology(fresh_ontology, tmp_path: Path):
    onto = fresh_ontology
    df = read_dataframe_from_csv_string(ANNUAL_CSV)
    populate_from_dataframe(onto, df, layout_name="annual_inventory")

    out = tmp_path / "test.owl"
    export_ontology(onto, str(out), format="rdfxml")
    assert out.exists()
    assert out.stat().st_size > 0

    ttl = tmp_path / "test.ttl"
    export_ontology(onto, str(ttl), format="turtle")
    assert ttl.exists()
    assert ttl.stat().st_size > 0
