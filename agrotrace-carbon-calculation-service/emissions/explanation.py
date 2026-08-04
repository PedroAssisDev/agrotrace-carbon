"""Contrato canônico de explicabilidade do cálculo (RF009 / RNF005).

Schema versionado: ``calc_explanation_v1``.
Não inventa valores numéricos ausentes — usa ``origin="absent"``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

SCHEMA_VERSION = "calc_explanation_v1"

GWP_ASSESSMENT_REPORT_AR4 = "IPCC AR4"
GWP_TIME_HORIZON_100Y = "100y"

FORMULA_CODES: dict[str, str] = {
    "enteric": "enteric_fermentation_ch4",
    "manure": "manure_management_ch4",
    "fertilizer": "fertilizer_n2o",
    "energy": "energy_co2",
    "total": "total_ghg_co2e",
}

FORMULA_TEXT: dict[str, str] = {
    "enteric": "Σ(headcount[categoria] × ef_enteric[categoria])",
    "manure": "Σ(n × peso × ef_esterco/dia × ef_CH4/esterco × dias)",
    "fertilizer": "N × ef_direto + N × fração_volatilizada × ef_indireto",
    "energy": "Σ(consumo[vetor] × ef_CO2[vetor])",
    "total": "CH4_total × GWP_CH4 + N2O × GWP_N2O + CO2",
}

FACTOR_UNITS: dict[str, str] = {
    "enteric_ch4_kg_per_animal": "kg CH4/animal/period",
    "manure_kg_per_kg_bw_per_day": "kg manure/kg BW/day",
    "manure_ch4_kg_per_kg_manure": "kg CH4/kg manure",
    "energy_co2_kg_per_unit": "kg CO2/unit",
    "fertilizer_factors.direct_n2o_emission_factor": "kg N2O/kg N",
    "fertilizer_factors.indirect_n2o_emission_factor": "kg N2O/kg N volatilized",
    "fertilizer_factors.fraction_n_volatilized": "fraction",
    "gwp": "kg CO2e/kg gas",
}


class ValueOrigin(str, Enum):
    CONFIGURED = "configured"
    DEFAULT = "default"
    INFERRED = "inferred"
    ABSENT = "absent"


@dataclass(frozen=True)
class TypedValue:
    """Valor com unidade e origem explícita."""

    value: float | None
    unit: str | None = None
    origin: str = ValueOrigin.DEFAULT.value
    source: str | None = None
    version: str | None = None
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "origin": self.origin,
            "source": self.source,
            "version": self.version,
        }


@dataclass(frozen=True)
class OriginArtifactRef:
    kind: str
    artifact_id: str | None = None
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "artifact_id": self.artifact_id, "label": self.label}


@dataclass(frozen=True)
class EmissionSourceExplanation:
    source_id: str
    label: str
    emission_source: str
    formula_code: str
    formula: str
    gas: str
    activity_data: list[TypedValue] = field(default_factory=list)
    factors: list[TypedValue] = field(default_factory=list)
    parameters: list[TypedValue] = field(default_factory=list)
    input_units: str | None = None
    output_units: str | None = None
    result_value: float | None = None
    result_unit: str | None = None
    co2e_kg: float | None = None
    origin_artifacts: list[OriginArtifactRef] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "label": self.label,
            "emission_source": self.emission_source,
            "formula_code": self.formula_code,
            "formula": self.formula,
            "gas": self.gas,
            "activity_data": [a.to_dict() for a in self.activity_data],
            "factors": [f.to_dict() for f in self.factors],
            "parameters": [p.to_dict() for p in self.parameters],
            "input_units": self.input_units,
            "output_units": self.output_units,
            "result_value": self.result_value,
            "result_unit": self.result_unit,
            "co2e_kg": self.co2e_kg,
            "origin_artifacts": [o.to_dict() for o in self.origin_artifacts],
        }


@dataclass(frozen=True)
class GwpSetExplanation:
    assessment_report: str
    time_horizon: str
    values: list[TypedValue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_report": self.assessment_report,
            "time_horizon": self.time_horizon,
            "values": [v.to_dict() for v in self.values],
        }


@dataclass(frozen=True)
class CalculationExplanation:
    """Payload canônico versionado de explicabilidade."""

    schema_version: str = SCHEMA_VERSION
    calculation_id: str | None = None
    result_id: str | None = None
    cycle_id: str | None = None
    computed_at: str = ""
    method_code: str = ""
    method_version: str = ""
    implementation_version: str = ""
    methodology_label: str = ""
    period: str | None = None
    temporal_granularity: str | None = None
    organizational_granularity: str = "property"
    days_in_period: int | None = None
    gwp: GwpSetExplanation | None = None
    sources: list[EmissionSourceExplanation] = field(default_factory=list)
    origin_artifacts: list[OriginArtifactRef] = field(default_factory=list)
    executed_by: str | None = None
    approved_by: str | None = None
    content_hash: str | None = None

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        data = {
            "schema_version": self.schema_version,
            "calculation_id": self.calculation_id,
            "result_id": self.result_id,
            "cycle_id": self.cycle_id,
            "computed_at": self.computed_at,
            "method": {
                "code": self.method_code,
                "version": self.method_version,
                "implementation_version": self.implementation_version,
                "methodology_label": self.methodology_label,
            },
            "period": self.period,
            "temporal_granularity": self.temporal_granularity,
            "organizational_granularity": self.organizational_granularity,
            "days_in_period": self.days_in_period,
            "gwp": self.gwp.to_dict() if self.gwp else None,
            "sources": [s.to_dict() for s in self.sources],
            "origin_artifacts": [o.to_dict() for o in self.origin_artifacts],
            "executed_by": self.executed_by,
            "approved_by": self.approved_by,
        }
        if include_hash:
            data["content_hash"] = self.content_hash or compute_explanation_hash(data)
        return data

    def factors_used_dict(self) -> dict[str, Any]:
        """Extrai o mapa legado factors_used a partir das fontes."""
        out: dict[str, Any] = {}
        for src in self.sources:
            for fac in src.factors:
                if fac.origin == ValueOrigin.ABSENT.value or fac.value is None:
                    continue
                name = fac.name or ""
                if name.startswith("gwp."):
                    bucket = out.setdefault("gwp", {})
                    bucket[name.split(".", 1)[1]] = fac.value
                elif name.startswith("fertilizer_factors."):
                    bucket = out.setdefault("fertilizer_factors", {})
                    bucket[name.split(".", 1)[1]] = fac.value
                elif "." in name:
                    group, key = name.split(".", 1)
                    bucket = out.setdefault(group, {})
                    bucket[key] = fac.value
                else:
                    # group-level flat: treat as single-key group when possible
                    out.setdefault(name, {})
        if self.gwp:
            gwp_bucket = out.setdefault("gwp", {})
            for v in self.gwp.values:
                if v.value is not None and v.name:
                    gwp_bucket[v.name] = v.value
        return out


def compute_explanation_hash(payload: Mapping[str, Any]) -> str:
    """Hash determinístico do payload (sem content_hash)."""
    cleaned = {k: v for k, v in payload.items() if k != "content_hash"}
    canonical = json.dumps(cleaned, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def explanation_from_dict(data: Mapping[str, Any]) -> CalculationExplanation:
    """Desserializa dict → CalculationExplanation (compatível com v1)."""
    method = data.get("method") or {}
    gwp_raw = data.get("gwp") or {}
    gwp = None
    if gwp_raw:
        values = [
            TypedValue(
                name=v.get("name"),
                value=v.get("value"),
                unit=v.get("unit"),
                origin=v.get("origin") or ValueOrigin.DEFAULT.value,
                source=v.get("source"),
                version=v.get("version"),
            )
            for v in (gwp_raw.get("values") or [])
        ]
        gwp = GwpSetExplanation(
            assessment_report=str(gwp_raw.get("assessment_report") or GWP_ASSESSMENT_REPORT_AR4),
            time_horizon=str(gwp_raw.get("time_horizon") or GWP_TIME_HORIZON_100Y),
            values=values,
        )

    sources: list[EmissionSourceExplanation] = []
    for s in data.get("sources") or []:
        sources.append(
            EmissionSourceExplanation(
                source_id=str(s.get("source_id") or ""),
                label=str(s.get("label") or ""),
                emission_source=str(s.get("emission_source") or s.get("source_id") or ""),
                formula_code=str(s.get("formula_code") or ""),
                formula=str(s.get("formula") or ""),
                gas=str(s.get("gas") or ""),
                activity_data=[
                    TypedValue(
                        name=a.get("name"),
                        value=a.get("value"),
                        unit=a.get("unit"),
                        origin=a.get("origin") or ValueOrigin.CONFIGURED.value,
                        source=a.get("source"),
                        version=a.get("version"),
                    )
                    for a in (s.get("activity_data") or [])
                ],
                factors=[
                    TypedValue(
                        name=f.get("name"),
                        value=f.get("value"),
                        unit=f.get("unit"),
                        origin=f.get("origin") or ValueOrigin.DEFAULT.value,
                        source=f.get("source"),
                        version=f.get("version"),
                    )
                    for f in (s.get("factors") or [])
                ],
                parameters=[
                    TypedValue(
                        name=p.get("name"),
                        value=p.get("value"),
                        unit=p.get("unit"),
                        origin=p.get("origin") or ValueOrigin.DEFAULT.value,
                        source=p.get("source"),
                        version=p.get("version"),
                    )
                    for p in (s.get("parameters") or [])
                ],
                input_units=s.get("input_units"),
                output_units=s.get("output_units") or s.get("result_unit"),
                result_value=s.get("result_value"),
                result_unit=s.get("result_unit"),
                co2e_kg=s.get("co2e_kg"),
                origin_artifacts=[
                    OriginArtifactRef(
                        kind=str(o.get("kind") or ""),
                        artifact_id=o.get("artifact_id"),
                        label=o.get("label"),
                    )
                    for o in (s.get("origin_artifacts") or [])
                ],
            )
        )

    return CalculationExplanation(
        schema_version=str(data.get("schema_version") or SCHEMA_VERSION),
        calculation_id=data.get("calculation_id"),
        result_id=data.get("result_id"),
        cycle_id=data.get("cycle_id"),
        computed_at=str(data.get("computed_at") or ""),
        method_code=str(method.get("code") or data.get("method_code") or ""),
        method_version=str(method.get("version") or data.get("method_version") or ""),
        implementation_version=str(
            method.get("implementation_version") or data.get("implementation_version") or ""
        ),
        methodology_label=str(method.get("methodology_label") or data.get("methodology_label") or ""),
        period=data.get("period"),
        temporal_granularity=data.get("temporal_granularity"),
        organizational_granularity=str(data.get("organizational_granularity") or "property"),
        days_in_period=data.get("days_in_period"),
        gwp=gwp,
        sources=sources,
        origin_artifacts=[
            OriginArtifactRef(
                kind=str(o.get("kind") or ""),
                artifact_id=o.get("artifact_id"),
                label=o.get("label"),
            )
            for o in (data.get("origin_artifacts") or [])
        ],
        executed_by=data.get("executed_by"),
        approved_by=data.get("approved_by"),
        content_hash=data.get("content_hash"),
    )


def _tv(
    name: str,
    value: float | None,
    *,
    unit: str | None,
    origin: str,
    source: str | None = None,
    version: str | None = None,
) -> TypedValue:
    return TypedValue(
        name=name,
        value=value,
        unit=unit,
        origin=origin if value is not None else ValueOrigin.ABSENT.value,
        source=source,
        version=version,
    )


def _factor_entries(
    group: str,
    values: Mapping[str, Any] | None,
    *,
    origins: Mapping[str, str] | None = None,
    default_origin: str = ValueOrigin.DEFAULT.value,
    source: str | None = None,
    version: str | None = None,
    unit: str | None = None,
) -> list[TypedValue]:
    out: list[TypedValue] = []
    data = dict(values or {})
    unit = unit or FACTOR_UNITS.get(group) or FACTOR_UNITS.get(f"{group}")
    for key, raw in data.items():
        if str(key).startswith("_"):
            continue
        try:
            val = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            val = None
        name = f"{group}.{key}" if group != "gwp" else f"gwp.{key}"
        if group == "fertilizer_factors":
            unit_key = f"fertilizer_factors.{key}"
            item_unit = FACTOR_UNITS.get(unit_key, unit)
        elif group == "gwp":
            item_unit = FACTOR_UNITS["gwp"]
            name = f"gwp.{key}"
        else:
            item_unit = unit
            name = f"{group}.{key}"
        origin = (origins or {}).get(key) or (default_origin if val is not None else ValueOrigin.ABSENT.value)
        out.append(_tv(name, val, unit=item_unit, origin=origin, source=source, version=version))
    return out


def build_calculation_explanation(
    *,
    flat: Mapping[str, float],
    inputs: Mapping[str, Any],
    factors_used: Mapping[str, Any],
    gwp: Mapping[str, float],
    method_code: str,
    method_version: str,
    implementation_version: str,
    methodology_label: str = "IPCC/IDF-compatible",
    temporal_granularity: str | None = None,
    period: str | None = None,
    days_in_period: int | None = None,
    factor_origins: Mapping[str, Mapping[str, str]] | None = None,
    factor_sources: Mapping[str, str] | None = None,
    origin_artifacts: list[OriginArtifactRef] | None = None,
    calculation_id: str | None = None,
    result_id: str | None = None,
    cycle_id: str | None = None,
    executed_by: str | None = None,
    approved_by: str | None = None,
    computed_at: datetime | None = None,
    gwp_assessment_report: str = GWP_ASSESSMENT_REPORT_AR4,
    gwp_time_horizon: str = GWP_TIME_HORIZON_100Y,
    absent_factor_keys: Mapping[str, list[str]] | None = None,
) -> CalculationExplanation:
    """Monta a explicação canônica a partir do resultado e fatores aplicados."""
    ts = (computed_at or datetime.now(timezone.utc)).isoformat()
    origins_map = {k: dict(v) for k, v in (factor_origins or {}).items()}
    sources_meta = dict(factor_sources or {})
    artifacts = list(origin_artifacts or [])

    headcounts = dict(inputs.get("headcounts_by_category") or {})
    body_weights = dict(inputs.get("body_weight_kg_by_category") or {})
    energy_vectors = dict(inputs.get("energy_consumption_by_vector") or {})
    nitrogen = inputs.get("nitrogen_applied_kg")
    days = days_in_period if days_in_period is not None else inputs.get("days_in_period")

    def _act(name: str, value: Any, unit: str) -> TypedValue:
        try:
            num = float(value) if value is not None else None
        except (TypeError, ValueError):
            num = None
        return _tv(
            name,
            num,
            unit=unit,
            origin=ValueOrigin.CONFIGURED.value if num is not None else ValueOrigin.ABSENT.value,
            source="activity_data",
        )

    enteric_factors = _factor_entries(
        "enteric_ch4_kg_per_animal",
        factors_used.get("enteric_ch4_kg_per_animal"),
        origins=origins_map.get("enteric_ch4_kg_per_animal"),
        default_origin=ValueOrigin.INFERRED.value
        if str(temporal_granularity or "").lower() in {"monthly", "month"}
        else ValueOrigin.DEFAULT.value,
        source=sources_meta.get("enteric_ch4_kg_per_animal"),
        version=method_version,
    )
    for key in (absent_factor_keys or {}).get("enteric_ch4_kg_per_animal") or []:
        if not any(f.name == f"enteric_ch4_kg_per_animal.{key}" for f in enteric_factors):
            enteric_factors.append(
                _tv(
                    f"enteric_ch4_kg_per_animal.{key}",
                    None,
                    unit=FACTOR_UNITS["enteric_ch4_kg_per_animal"],
                    origin=ValueOrigin.ABSENT.value,
                )
            )

    gwp_ch4 = float(gwp.get("CH4")) if gwp.get("CH4") is not None else None
    gwp_n2o = float(gwp.get("N2O")) if gwp.get("N2O") is not None else None
    ch4_enteric = float(flat.get("ch4_enteric_kg") or 0)
    ch4_manure = float(flat.get("ch4_manure_kg") or 0)
    n2o_fert = float(flat.get("n2o_fertilizer_kg") or 0)
    co2_energy = float(flat.get("co2_energy_kg") or 0)

    source_list: list[EmissionSourceExplanation] = [
        EmissionSourceExplanation(
            source_id="enteric",
            label="Fermentação entérica",
            emission_source="enteric_fermentation",
            formula_code=FORMULA_CODES["enteric"],
            formula=FORMULA_TEXT["enteric"],
            gas="CH4",
            activity_data=[_act(f"headcount.{k}", v, "animals") for k, v in headcounts.items()],
            factors=enteric_factors,
            input_units="animals; kg CH4/animal/period",
            output_units="kg CH4",
            result_value=ch4_enteric,
            result_unit="kg CH4",
            co2e_kg=(ch4_enteric * gwp_ch4) if gwp_ch4 is not None else None,
            origin_artifacts=artifacts,
        ),
        EmissionSourceExplanation(
            source_id="manure",
            label="Manejo de dejetos",
            emission_source="manure_management",
            formula_code=FORMULA_CODES["manure"],
            formula=FORMULA_TEXT["manure"],
            gas="CH4",
            activity_data=(
                [_act(f"headcount.{k}", v, "animals") for k, v in headcounts.items()]
                + [_act(f"body_weight.{k}", v, "kg") for k, v in body_weights.items()]
                + [_act("days_in_period", days, "days")]
            ),
            factors=(
                _factor_entries(
                    "manure_kg_per_kg_bw_per_day",
                    factors_used.get("manure_kg_per_kg_bw_per_day"),
                    origins=origins_map.get("manure_kg_per_kg_bw_per_day"),
                    default_origin=ValueOrigin.DEFAULT.value,
                    source=sources_meta.get("manure_kg_per_kg_bw_per_day"),
                    version=method_version,
                )
                + _factor_entries(
                    "manure_ch4_kg_per_kg_manure",
                    factors_used.get("manure_ch4_kg_per_kg_manure"),
                    origins=origins_map.get("manure_ch4_kg_per_kg_manure"),
                    default_origin=ValueOrigin.DEFAULT.value,
                    source=sources_meta.get("manure_ch4_kg_per_kg_manure"),
                    version=method_version,
                )
            ),
            input_units="animals; kg BW; days",
            output_units="kg CH4",
            result_value=ch4_manure,
            result_unit="kg CH4",
            co2e_kg=(ch4_manure * gwp_ch4) if gwp_ch4 is not None else None,
            origin_artifacts=artifacts,
        ),
        EmissionSourceExplanation(
            source_id="fertilizer",
            label="Fertilizantes N",
            emission_source="fertilizer_n2o",
            formula_code=FORMULA_CODES["fertilizer"],
            formula=FORMULA_TEXT["fertilizer"],
            gas="N2O",
            activity_data=[_act("nitrogen_applied_kg", nitrogen, "kg N")],
            factors=_factor_entries(
                "fertilizer_factors",
                factors_used.get("fertilizer_factors"),
                origins=origins_map.get("fertilizer_factors"),
                default_origin=ValueOrigin.DEFAULT.value,
                source=sources_meta.get("fertilizer_factors"),
                version=method_version,
            ),
            input_units="kg N",
            output_units="kg N2O",
            result_value=n2o_fert,
            result_unit="kg N2O",
            co2e_kg=(n2o_fert * gwp_n2o) if gwp_n2o is not None else None,
            origin_artifacts=artifacts,
        ),
        EmissionSourceExplanation(
            source_id="energy",
            label="Energia",
            emission_source="energy_combustion",
            formula_code=FORMULA_CODES["energy"],
            formula=FORMULA_TEXT["energy"],
            gas="CO2",
            activity_data=[_act(f"energy.{k}", v, "unit") for k, v in energy_vectors.items()],
            factors=_factor_entries(
                "energy_co2_kg_per_unit",
                factors_used.get("energy_co2_kg_per_unit"),
                origins=origins_map.get("energy_co2_kg_per_unit"),
                default_origin=ValueOrigin.DEFAULT.value,
                source=sources_meta.get("energy_co2_kg_per_unit"),
                version=method_version,
            ),
            input_units="consumption units",
            output_units="kg CO2",
            result_value=co2_energy,
            result_unit="kg CO2",
            co2e_kg=co2_energy,
            origin_artifacts=artifacts,
        ),
        EmissionSourceExplanation(
            source_id="total",
            label="Total GEE",
            emission_source="total_ghg",
            formula_code=FORMULA_CODES["total"],
            formula=FORMULA_TEXT["total"],
            gas="CO2e",
            activity_data=[],
            factors=_factor_entries(
                "gwp",
                gwp or factors_used.get("gwp"),
                origins=origins_map.get("gwp"),
                default_origin=ValueOrigin.DEFAULT.value,
                source=sources_meta.get("gwp") or "ipcc_ar4",
                version=gwp_assessment_report,
            ),
            parameters=[],
            input_units="kg CH4; kg N2O; kg CO2",
            output_units="kg CO2e",
            result_value=float(flat.get("co2e_total_kg") or 0),
            result_unit="kg CO2e",
            co2e_kg=float(flat.get("co2e_total_kg") or 0),
            origin_artifacts=artifacts,
        ),
    ]

    gwp_values = _factor_entries(
        "gwp",
        gwp,
        origins=origins_map.get("gwp"),
        default_origin=ValueOrigin.DEFAULT.value,
        source=sources_meta.get("gwp") or "ipcc_ar4",
        version=gwp_assessment_report,
    )
    # Normalize gwp TypedValue names to gas codes only in GwpSetExplanation
    gwp_set_values = [
        TypedValue(
            name=(v.name or "").split(".")[-1],
            value=v.value,
            unit=v.unit,
            origin=v.origin,
            source=v.source,
            version=v.version,
        )
        for v in gwp_values
    ]

    explanation = CalculationExplanation(
        schema_version=SCHEMA_VERSION,
        calculation_id=calculation_id,
        result_id=result_id,
        cycle_id=cycle_id,
        computed_at=ts,
        method_code=method_code,
        method_version=method_version,
        implementation_version=implementation_version,
        methodology_label=methodology_label,
        period=period,
        temporal_granularity=temporal_granularity,
        organizational_granularity="property",
        days_in_period=int(days) if days is not None else None,
        gwp=GwpSetExplanation(
            assessment_report=gwp_assessment_report,
            time_horizon=gwp_time_horizon,
            values=gwp_set_values,
        ),
        sources=source_list,
        origin_artifacts=artifacts,
        executed_by=executed_by,
        approved_by=approved_by,
    )
    payload = explanation.to_dict(include_hash=False)
    return replace(explanation, content_hash=compute_explanation_hash(payload))
