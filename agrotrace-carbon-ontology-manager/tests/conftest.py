"""Pytest fixtures for AgroMRV-O Lite."""

from __future__ import annotations

import pytest

from ontology.builder import build_base_ontology, build_full_ontology
from ontology.catalogs import populate_catalogs


@pytest.fixture
def base_ontology():
    return build_base_ontology()


@pytest.fixture
def fresh_ontology():
    return build_full_ontology()
