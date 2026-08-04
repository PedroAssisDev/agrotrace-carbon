"""Export AgroMRV-O Lite ontology to RDF/XML, OWL, and Turtle."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph


def export_ontology(onto: object, output_path: str, format: str = "rdfxml") -> None:
    """Export ontology to file. Supports rdfxml/owl and turtle/ttl."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = format.lower()
    if fmt in ("rdfxml", "owl", "rdf"):
        onto.save(str(path), format="rdfxml")
        return
    if fmt in ("turtle", "ttl"):
        _export_turtle(onto, path)
        return
    raise ValueError(f"Unsupported export format: {format}")


def _export_turtle(onto: object, path: Path) -> None:
    """Export via rdflib for reliable Turtle serialization."""
    tmp_rdf = path.with_suffix(".tmp.rdf")
    onto.save(str(tmp_rdf), format="rdfxml")
    g = Graph()
    g.parse(str(tmp_rdf), format="xml")
    g.serialize(destination=str(path), format="turtle")
    tmp_rdf.unlink(missing_ok=True)
