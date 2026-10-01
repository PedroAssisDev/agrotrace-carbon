"""Exporta ciclos publicados para o CSV canônico do model-training-service."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

import config
from services.blockchain_view_service import has_final_ontology_published
from utils.file_helpers import list_cycles

logger = logging.getLogger("agrotrace.training_export")

CANONICAL_COLUMNS = [
    "property_id",
    "period",
    "granularity",
    "lactating_cows",
    "milk_production_liters",
    "total_ghg_emissions_tco2e",
    "approval_status",
    "publication_status",
]

EXPORT_FILENAME = "approved_results_from_cycles.csv"


def approved_results_export_path() -> Path:
    return Path(config.MODEL_TRAINING_PROCESSED_DIR) / EXPORT_FILENAME


def export_approved_results_from_cycles(
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Materializa CSV canônico a partir dos ciclos publicados/aprovados."""
    destination = Path(output_path or approved_results_export_path())
    destination.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    properties: set[str] = set()

    for cycle in list_cycles():
        mapped = _cycle_to_training_row(cycle)
        if mapped.get("ok"):
            row = mapped["row"]
            rows.append(row)
            properties.add(str(row["property_id"]))
        else:
            skipped.append(
                {
                    "cycle_id": str(cycle.get("cycle_id") or ""),
                    "reason": str(mapped.get("reason") or "skip"),
                }
            )

    # Dedupa por chave natural (mantém o último ciclo mapeado).
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row["property_id"]), str(row["period"]), str(row["granularity"]))
        by_key[key] = {col: row[col] for col in CANONICAL_COLUMNS}
    rows = [by_key[k] for k in sorted(by_key)]

    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    result = {
        "path": str(destination.resolve()),
        "row_count": len(rows),
        "properties": sorted(properties),
        "skipped": len(skipped),
        "skipped_samples": skipped[:20],
    }
    logger.info(
        "[TRAIN_EXPORT] wrote %s rows for %s properties → %s (skipped=%s)",
        result["row_count"],
        len(properties),
        result["path"],
        result["skipped"],
    )
    return result


def _cycle_to_training_row(cycle: dict[str, Any]) -> dict[str, Any]:
    if not has_final_ontology_published(cycle):
        return {"ok": False, "reason": "not_published"}

    review = (cycle.get("calculation_review") or {}).get("status")
    approval = (cycle.get("approval") or {}).get("decision")
    step_approval = ((cycle.get("steps") or {}).get("approval") or {}).get("status")
    if not (
        review == "APPROVED"
        or approval == "APPROVED"
        or step_approval == "APPROVED"
    ):
        return {"ok": False, "reason": "not_approved"}

    property_id = cycle.get("property_id")
    if not property_id:
        return {"ok": False, "reason": "missing_property_id"}

    period = _normalize_period(cycle.get("reporting_period"))
    if not period:
        return {"ok": False, "reason": "missing_period"}

    granularity = _normalize_granularity(
        cycle.get("granularity") or cycle.get("frequency") or "monthly"
    )
    if granularity not in {"monthly", "annual"}:
        return {"ok": False, "reason": f"unsupported_granularity:{granularity}"}

    record = _normalized_record(cycle)
    cows = _to_float(
        record.get("lactating_cows")
        if record.get("lactating_cows") is not None
        else record.get("number_of_lactating_cows")
    )
    milk = _to_float(
        record.get("milk_production")
        if record.get("milk_production") is not None
        else record.get("milk_production_liters")
        if record.get("milk_production_liters") is not None
        else record.get("total_milk_production")
    )

    calc = cycle.get("calculation") or {}
    co2e_kg = _to_float(calc.get("co2e_total_kg"))
    if co2e_kg is None:
        pub = cycle.get("publication") or {}
        approved = pub.get("approved_results") or {}
        co2e_kg = _to_float(approved.get("co2e_total_kg"))
    emissions_t = None if co2e_kg is None else co2e_kg / 1000.0

    if cows is None or milk is None or emissions_t is None:
        return {
            "ok": False,
            "reason": f"missing_metrics:cows={cows is not None},milk={milk is not None},emis={emissions_t is not None}",
        }

    return {
        "ok": True,
        "row": {
            "property_id": str(property_id),
            "period": period,
            "granularity": granularity,
            "lactating_cows": cows,
            "milk_production_liters": milk,
            "total_ghg_emissions_tco2e": emissions_t,
            "approval_status": "approved",
            "publication_status": "published",
        },
    }


def _normalized_record(cycle: dict[str, Any]) -> dict[str, Any]:
    data = cycle.get("normalized_data")
    if isinstance(data, list) and data:
        first = data[0]
        return first if isinstance(first, dict) else {}
    if isinstance(data, dict):
        return data
    wrapper = cycle.get("wrapper") or {}
    payload = wrapper.get("normalized_payload")
    if isinstance(payload, list) and payload:
        first = payload[0]
        return first if isinstance(first, dict) else {}
    if isinstance(payload, dict):
        return payload
    return {}


def _normalize_period(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    # YYYY-MM or YYYY-MM-DD → month/year start
    if len(text) == 7 and text[4] == "-":
        return f"{text}-01"
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    if len(text) == 4 and text.isdigit():
        return f"{text}-01-01"
    return text


def _normalize_granularity(value: Any) -> str:
    text = str(value or "monthly").strip().lower()
    if text in {"month", "monthly", "mensal", "m"}:
        return "monthly"
    if text in {"year", "annual", "yearly", "anual", "a", "y"}:
        return "annual"
    return text


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number
