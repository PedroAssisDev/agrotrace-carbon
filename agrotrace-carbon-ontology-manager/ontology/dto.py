"""DTOs de projeção ontológica para consumidores (frontend adapters)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _base_meta(
    *,
    ontology_path: str | None,
    ontology_version: str | None,
    cycle_id: str | None = None,
    property_id: str | None = None,
    data_status: str | None = None,
) -> dict[str, Any]:
    return {
        "source": "ontology",
        "ontology_path": ontology_path,
        "ontology_version": ontology_version,
        "cycle_id": cycle_id,
        "property_id": property_id,
        "data_status": data_status,
    }


@dataclass
class PropertyOptionDTO:
    property_id: str
    name: str
    municipality: str = ""
    state: str = ""
    ontology_path: str | None = None
    ontology_version: str | None = None
    source: str = "ontology"
    data_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.update(_base_meta(
            ontology_path=self.ontology_path,
            ontology_version=self.ontology_version,
            property_id=self.property_id,
            data_status=self.data_status,
        ))
        return d


@dataclass
class CycleContextDTO:
    cycle_id: str
    property_id: str
    property_name: str | None
    reporting_period: str
    temporal_granularity: str
    organizational_granularity: str
    status: str
    period_start: str | None = None
    period_end: str | None = None
    ontology_path: str | None = None
    ontology_version: str | None = None
    published_ontology_path: str | None = None
    source: str = "ontology"
    data_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.update(_base_meta(
            ontology_path=self.ontology_path,
            ontology_version=self.ontology_version,
            cycle_id=self.cycle_id,
            property_id=self.property_id,
            data_status=self.data_status or self.status,
        ))
        return d


@dataclass
class EmissionResultDTO:
    result_id: str
    result_key: str
    cycle_id: str
    property_id: str | None
    formula_id: str | None
    gas: str
    emission_source: str
    value: float | None
    unit: str | None
    co2e_value: float | None
    co2e_unit: str | None
    status: str
    reporting_period: str | None
    temporal_granularity: str | None
    ontology_path: str | None = None
    ontology_version: str | None = None
    source: str = "ontology"
    data_status: str | None = None
    calculated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.update(_base_meta(
            ontology_path=self.ontology_path,
            ontology_version=self.ontology_version,
            cycle_id=self.cycle_id,
            property_id=self.property_id,
            data_status=self.data_status or self.status,
        ))
        return d


@dataclass
class EmissionSummaryDTO:
    cycle_id: str
    property_id: str | None
    co2e_total_kg: float | None
    intensity: float | None
    milk_liters: float | None
    animals: float | None
    by_source: dict[str, float] = field(default_factory=dict)
    by_gas: dict[str, float] = field(default_factory=dict)
    ontology_path: str | None = None
    ontology_version: str | None = None
    source: str = "ontology"
    data_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.update(_base_meta(
            ontology_path=self.ontology_path,
            ontology_version=self.ontology_version,
            cycle_id=self.cycle_id,
            property_id=self.property_id,
            data_status=self.data_status,
        ))
        return d
