"""Build base ontology (TBox + catalogs)."""

from __future__ import annotations

from ontology.catalogs import populate_catalogs
from ontology.schema import define_schema


def build_base_ontology(base_iri: str = "http://example.org/agromrv-lite#") -> object:
    """Create AgroMRV-O Lite TBox and return the ontology object."""
    return define_schema(base_iri)


def build_full_ontology(base_iri: str = "http://example.org/agromrv-lite#") -> object:
    """Create TBox and populate internal catalogs."""
    onto = build_base_ontology(base_iri)
    populate_catalogs(onto)
    return onto
