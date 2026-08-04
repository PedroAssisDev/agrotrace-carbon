"""Shared pytest fixtures for the provenance service test suite."""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-mark items by directory + skip integration when DBs aren't available."""

    for item in items:
        path = str(item.path)
        if "/integration/" in path or "\\integration\\" in path:
            item.add_marker(pytest.mark.integration)
        if "/invariants/" in path or "\\invariants\\" in path:
            item.add_marker(pytest.mark.invariants)
        if "/unit/" in path or "\\unit\\" in path:
            item.add_marker(pytest.mark.unit)

    skip_integration = os.getenv("PROV_SKIP_INTEGRATION_TESTS", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if skip_integration:
        skip = pytest.mark.skip(
            reason="PROV_SKIP_INTEGRATION_TESTS is set; skipping integration and invariant tests"
        )
        for item in items:
            if "integration" in item.keywords or "invariants" in item.keywords:
                item.add_marker(skip)
