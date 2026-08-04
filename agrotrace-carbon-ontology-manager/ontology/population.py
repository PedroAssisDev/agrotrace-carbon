"""Populate ontology ABox from normalized DataFrames/CSVs."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd

from ontology import iri as iri_mod
from ontology.catalogs import get_catalog_individual
from ontology.mappings import (
    get_expected_unit_for_variable,
    get_observation_class_for_variable,
    is_context_column,
    is_qualitative_variable,
    resolve_canonical_variable,
)

ORG_KEY = "_organizational_context"
TEMP_KEY = "_temporal_context"
DEFAULT_DELIM = ";_;"


def _uncsv_quoted_field(raw: str) -> str:
    s = raw.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1].replace('""', '"')
    return s


def parse_org_context(raw: str | dict | None) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw or not str(raw).strip():
        return {}
    return json.loads(_uncsv_quoted_field(str(raw)))


def parse_temporal_context(raw: str | dict | None) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw or not str(raw).strip():
        return {}
    return json.loads(_uncsv_quoted_field(str(raw)))


def temporal_instant_date(tc: dict[str, Any]) -> str | None:
    if tc.get("type") == "instant":
        return str(tc.get("date") or tc.get("value") or "")
    return None


def temporal_granularity(tc: dict[str, Any]) -> str | None:
    return tc.get("granularity")


def temporal_key(tc: dict[str, Any], row: dict[str, Any]) -> str:
    gran = temporal_granularity(tc) or "unknown"
    if tc.get("type") == "interval":
        start = tc.get("start") or row.get("period_start") or ""
        end = tc.get("end") or row.get("period_end") or ""
        return f"{gran}_{start}_{end}"
    if tc.get("type") == "instant":
        d = temporal_instant_date(tc) or row.get("date") or ""
        return f"{gran}_{d}"
    year = row.get("year") or ""
    return f"{gran}_{year}"


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    s = str(value).strip()
    return s == "" or s.lower() in ("nan", "none", "null")


def _is_numeric(value: Any) -> bool:
    if _is_empty(value):
        return False
    try:
        float(str(value).replace(",", "."))
        return True
    except ValueError:
        return False


def _to_float(value: Any) -> float:
    return float(str(value).replace(",", "."))


class PopulationCache:
    def __init__(self) -> None:
        self.org_contexts: dict[str, object] = {}
        self.temp_contexts: dict[str, object] = {}
        self.properties: dict[str, object] = {}
        self.lots: dict[str, object] = {}
        self.animals: dict[str, object] = {}
        self.records: dict[str, object] = {}


def _get_class(onto: object, name: str) -> type:
    return getattr(onto, name)


def _ensure_org_context(onto: object, cache: PopulationCache, org: dict[str, Any]) -> object:
    identifier = str(org.get("identifier") or org.get("id") or "unknown")
    gran = str(org.get("granularity") or "property")
    key = iri_mod.org_context_iri(identifier, gran)
    if key in cache.org_contexts:
        return cache.org_contexts[key]
    with onto:
        ind = _get_class(onto, "OrganizationalContext")(key)
        ind.hasIdentifier = [identifier]
        ind.hasOrganizationalGranularity = [gran]
    cache.org_contexts[key] = ind
    return ind


def _ensure_temp_context(
    onto: object, cache: PopulationCache, tc: dict[str, Any], row: dict[str, Any]
) -> object:
    key = iri_mod.temporal_iri(temporal_key(tc, row))
    if key in cache.temp_contexts:
        return cache.temp_contexts[key]
    with onto:
        ind = _get_class(onto, "TemporalContext")(key)
        ind.hasTemporalType = [str(tc.get("type") or "unknown")]
        if tc.get("granularity"):
            ind.hasTemporalGranularity = [str(tc["granularity"])]
        if tc.get("type") == "interval":
            if tc.get("start"):
                ind.hasStartDate = [str(tc["start"])]
            if tc.get("end"):
                ind.hasEndDate = [str(tc["end"])]
        if tc.get("type") == "instant":
            d = temporal_instant_date(tc) or row.get("date")
            if d:
                ind.hasDate = [str(d)]
        if row.get("year"):
            ind.hasYear = [str(row["year"])]
        if row.get("period_start"):
            ind.hasStartDate = [str(row["period_start"])]
        if row.get("period_end"):
            ind.hasEndDate = [str(row["period_end"])]
    cache.temp_contexts[key] = ind
    return ind


def _ensure_property(
    onto: object,
    cache: PopulationCache,
    org: dict[str, Any],
    row: dict[str, Any],
) -> object:
    prop_id = str(
        row.get("property_id")
        or row.get("property_name")
        or org.get("identifier")
        or "unknown"
    )
    key = iri_mod.property_iri(prop_id)
    if key in cache.properties:
        return cache.properties[key]
    with onto:
        ind = _get_class(onto, "Property")(key)
        ind.hasIdentifier = [prop_id]
        if row.get("property_name"):
            ind.hasPropertyName = [str(row["property_name"])]
        if row.get("owner_name"):
            ind.hasOwnerName = [str(row["owner_name"])]
        if row.get("information_responsible"):
            ind.hasInformationResponsible = [str(row["information_responsible"])]
        if row.get("location"):
            ind.hasLocationName = [str(row["location"])]
    cache.properties[key] = ind
    return ind


def _ensure_lot(
    onto: object,
    cache: PopulationCache,
    lot_id: str,
    property_id: str,
) -> object:
    from ontology.cycle_model import upsert_lot

    key = iri_mod.lot_iri(lot_id)
    if key in cache.lots:
        return cache.lots[key]
    lot = upsert_lot(onto, lot_id=lot_id, property_id=property_id)
    cache.lots[key] = lot
    return lot


def _ensure_animal(
    onto: object,
    cache: PopulationCache,
    animal_id: str,
    *,
    property_id: str,
    lot_id: str | None = None,
) -> object:
    from ontology.cycle_model import upsert_animal

    key = iri_mod.animal_iri(animal_id)
    if key in cache.animals:
        animal = cache.animals[key]
        # Refresh links if lot newly provided
        if lot_id and not list(getattr(animal, "belongsToLot", None) or []):
            return upsert_animal(
                onto,
                animal_id=animal_id,
                property_id=property_id,
                lot_id=lot_id,
            )
        return animal
    animal = upsert_animal(
        onto,
        animal_id=animal_id,
        property_id=property_id,
        lot_id=lot_id,
    )
    cache.animals[key] = animal
    return animal


def detect_record_class_name(row: dict[str, Any], org: dict[str, Any], tc: dict[str, Any]) -> str:
    gran = (temporal_granularity(tc) or "").lower()
    org_gran = (org.get("granularity") or "").lower()
    has_animal = not _is_empty(row.get("animal_id"))
    has_date = not _is_empty(row.get("date")) or tc.get("type") == "instant"
    has_milk = not _is_empty(row.get("milk"))
    has_weight = not _is_empty(row.get("weight"))
    has_dmi = not _is_empty(row.get("dry_matter_intake"))
    has_energy_density = not _is_empty(row.get("energy_density"))
    has_period = not _is_empty(row.get("period_start")) and not _is_empty(row.get("period_end"))

    if has_animal and has_date and has_milk and has_weight:
        if has_dmi and has_energy_density:
            return "DailyAnimalNutritionRecord"
        return "DailyAnimalProductionRecord"
    if org_gran == "property" and gran == "year":
        return "AnnualPropertyInventoryRecord"
    if has_period or gran == "month":
        return "MonthlyPropertyRecord"
    return "DataRecord"


def populate_from_dataframe(
    onto: object,
    df: pd.DataFrame,
    layout_name: str | None = None,
    source_name: str | None = None,
) -> object:
    """Populate ontology instances from a normalized DataFrame."""
    cache = PopulationCache()
    gran_from_batch: str | None = None

    for _, series in df.iterrows():
        row = {k: ("" if pd.isna(v) else v) for k, v in series.to_dict().items()}
        org = parse_org_context(row.get(ORG_KEY, ""))
        tc = parse_temporal_context(row.get(TEMP_KEY, ""))
        gran_from_batch = temporal_granularity(tc)

        org_ctx = _ensure_org_context(onto, cache, org)
        temp_ctx = _ensure_temp_context(onto, cache, tc, row)
        prop = _ensure_property(onto, cache, org, row)
        property_id = str(
            row.get("property_id")
            or org.get("identifier")
            or _get_dp_safe(prop)
            or "unknown"
        )

        lot = None
        lot_id = None if _is_empty(row.get("lot_id")) else str(row["lot_id"])
        if lot_id is None and (org.get("granularity") or "").lower() in ("lot", "lote"):
            # identifier at lot granularity may be the lot id
            cand = org.get("identifier")
            if cand and str(cand) != property_id:
                lot_id = str(cand)
        if lot_id:
            lot = _ensure_lot(onto, cache, lot_id, property_id)

        animal = None
        if not _is_empty(row.get("animal_id")):
            animal = _ensure_animal(
                onto,
                cache,
                str(row["animal_id"]),
                property_id=property_id,
                lot_id=lot_id,
            )

        record_cls_name = detect_record_class_name(row, org, tc)
        org_id = str(org.get("identifier") or row.get("property_id") or "unknown")
        rec_key = iri_mod.record_iri(org_id, temporal_key(tc, row))
        if rec_key not in cache.records:
            with onto:
                record = _get_class(onto, record_cls_name)(rec_key)
                record.hasOrganizationalContext = [org_ctx]
                record.hasTemporalContext = [temp_ctx]
                record.refersToProperty = [prop]
                if lot:
                    record.refersToLot = [lot]
                if animal:
                    record.refersToAnimal = [animal]
                if layout_name:
                    record.hasSourceLayout = [layout_name]
                if source_name:
                    record.hasIdentifier = [source_name]
            cache.records[rec_key] = record
        else:
            record = cache.records[rec_key]

        for col, raw_val in row.items():
            if is_context_column(col):
                continue
            if _is_empty(raw_val):
                continue

            canonical = resolve_canonical_variable(col, layout_name)
            obs_class_name = get_observation_class_for_variable(col, layout_name)
            unit_name = get_expected_unit_for_variable(canonical, gran_from_batch)
            obs_key = iri_mod.observation_iri(rec_key, canonical)

            with onto:
                obs = _get_class(onto, obs_class_name)(obs_key)
                obs.belongsToRecord = [record]
                obs.hasOrganizationalContext = [org_ctx]
                obs.hasTemporalContext = [temp_ctx]
                obs.refersToProperty = [prop]
                if lot:
                    obs.refersToLot = [lot]
                if animal:
                    obs.refersToAnimal = [animal]
                var_ind = get_catalog_individual(onto, "variables", canonical)
                if var_ind:
                    obs.observesVariable = [var_ind]
                unit_ind = get_catalog_individual(onto, "units", unit_name)
                if unit_ind:
                    obs.hasUnit = [unit_ind]
                obs.hasOriginalColumnName = [col]

                if is_qualitative_variable(canonical) or not _is_numeric(raw_val):
                    obs.hasTextValue = [str(raw_val)]
                else:
                    obs.hasNumericValue = [_to_float(raw_val)]

                record.hasObservation.append(obs)

    return onto


def _get_dp_safe(ind: object) -> str | None:
    vals = list(getattr(ind, "hasIdentifier", None) or [])
    return str(vals[0]) if vals else None


def populate_from_csv(
    onto: object,
    csv_path: str,
    delimiter: str = DEFAULT_DELIM,
    layout_name: str | None = None,
    source_name: str | None = None,
) -> object:
    df = pd.read_csv(
        csv_path, sep=delimiter, engine="python", dtype=str, keep_default_na=False
    )
    return populate_from_dataframe(onto, df, layout_name=layout_name, source_name=source_name)


def read_dataframe_from_csv_string(csv_text: str, delimiter: str = DEFAULT_DELIM) -> pd.DataFrame:
    return pd.read_csv(
        StringIO(csv_text), sep=delimiter, engine="python", dtype=str, keep_default_na=False
    )
