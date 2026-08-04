"""Deterministic IRI generation for AgroMRV-O Lite."""

from __future__ import annotations

import hashlib
import re
import unicodedata


def normalize_token(value: str) -> str:
    """Normalize a token for use in local IRI fragments."""
    if not value:
        return "unknown"
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[\s\-–—/\\]+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def short_hash(*parts: str, length: int = 8) -> str:
    """Stable short hash for collision avoidance."""
    payload = "|".join(normalize_token(p) for p in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def property_iri(identifier: str) -> str:
    return f"property_{normalize_token(identifier)}"


def org_context_iri(identifier: str, granularity: str | None = None) -> str:
    gran = normalize_token(granularity) if granularity else "org"
    return f"org_{gran}_{normalize_token(identifier)}"


def temporal_iri(key: str) -> str:
    return f"time_{normalize_token(key)}"


def record_iri(org_key: str, temporal_key: str, suffix: str = "") -> str:
    base = f"record_{normalize_token(org_key)}_{normalize_token(temporal_key)}"
    if suffix:
        base = f"{base}_{normalize_token(suffix)}"
    return base


def observation_iri(record_key: str, variable: str) -> str:
    return f"obs_{normalize_token(record_key)}_{normalize_token(variable)}"


def animal_iri(animal_id: str) -> str:
    return f"animal_{normalize_token(animal_id)}"


def individual_name(prefix: str, *parts: str) -> str:
    tokens = [normalize_token(p) for p in parts if p]
    name = "_".join([normalize_token(prefix), *tokens]) if tokens else normalize_token(prefix)
    return name


def cycle_iri(cycle_id: str) -> str:
    return f"cycle_{normalize_token(cycle_id)}"


def result_iri(result_key: str) -> str:
    return f"result_{normalize_token(result_key)}_{short_hash(result_key)}"


def make_result_key(
    *,
    cycle_id: str,
    formula_id: str,
    gas: str,
    period: str,
    granularity: str,
    org_scope: str = "property",
    emission_source: str = "",
) -> str:
    return "|".join(
        [
            normalize_token(cycle_id),
            normalize_token(formula_id or emission_source),
            normalize_token(gas),
            normalize_token(period),
            normalize_token(granularity),
            normalize_token(org_scope),
            normalize_token(emission_source),
        ]
    )
