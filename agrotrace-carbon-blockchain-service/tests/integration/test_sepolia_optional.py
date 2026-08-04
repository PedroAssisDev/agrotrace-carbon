"""Sepolia tests are skipped unless explicitly enabled with configuration."""

from __future__ import annotations

import os

import pytest

from app.shared.config import Settings


def _sepolia_enabled() -> bool:
    if os.environ.get("RUN_SEPOLIA_TESTS") != "1":
        return False
    settings = Settings()
    return settings.sepolia_ready()


pytestmark = pytest.mark.sepolia


@pytest.mark.skipif(not _sepolia_enabled(), reason="Sepolia env / RUN_SEPOLIA_TESTS not set")
def test_sepolia_chain_id_is_11155111() -> None:
    settings = Settings()
    assert settings.sepolia_chain_id == 11155111
    assert settings.sepolia_ready()
