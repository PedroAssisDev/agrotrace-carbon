"""Deterministic UUIDs and idempotency keys for demo scenarios."""

from __future__ import annotations

import uuid
from typing import Any

DEMO_NS = uuid.UUID("22222222-2222-2222-2222-222222222222")


def demo_id(*parts: str) -> uuid.UUID:
    return uuid.uuid5(DEMO_NS, "|".join(parts))


def idem_key(*parts: str) -> str:
    return "|".join(parts)


def run_code_monthly(month: int) -> str:
    return f"demo_repo_boa_vista_2026-{month:02d}"


def run_code_daily_january(day: int) -> str:
    return f"demo_repo_santa_clara_2026-01-{day:02d}"


def run_code_monthly_aggregate_santa(month: int) -> str:
    return f"demo_repo_santa_clara_2026-m{month:02d}-agg"


def run_code_annual_santa() -> str:
    return "demo_repo_santa_clara_2026-annual"


def run_code_annual_boa_vista() -> str:
    return "demo_repo_boa_vista_2026-annual"


def case_id(case: str, *parts: str) -> uuid.UUID:
    return demo_id(case, *parts)


def content_hash_label(label: str) -> str:
    from provenance_service.domain.shared.hashing import compute_hash_hex

    return compute_hash_hex({"demo_repository_full_population": label})
