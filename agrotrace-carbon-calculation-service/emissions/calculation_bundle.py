"""Resultado completo de um ciclo de cálculo de emissões."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from emissions.models import CalculationResult, TotalGhgResult


@dataclass(frozen=True)
class ProvenanceMetadata:
    """Metadados mínimos para integração futura com traceability-service."""

    method_code: str
    method_version: str
    implementation_version: str
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class CalculationBundle:
    """Pacote de sub-resultados, total, indicadores e proveniência."""

    enteric: CalculationResult
    manure: CalculationResult
    fertilizer: CalculationResult
    energy: CalculationResult
    total: TotalGhgResult
    indicators: dict[str, CalculationResult] = field(default_factory=dict)
    provenance: ProvenanceMetadata | None = None

    def to_flat_dict(self) -> dict[str, float]:
        """Converte para colunas numéricas (CSV / DataFrame)."""
        out: dict[str, float] = {
            "ch4_enteric_kg": self.enteric.value,
            "ch4_manure_kg": self.manure.value,
            "n2o_fertilizer_kg": self.fertilizer.value,
            "co2_energy_kg": self.energy.value,
            "co2e_total_kg": self.total.co2e_kg,
            "co2e_ch4_portion_kg": self.total.ch4_co2e_kg,
            "co2e_n2o_portion_kg": self.total.n2o_co2e_kg,
            "co2_energy_portion_kg": self.total.co2_kg,
        }
        for name, indicator in self.indicators.items():
            out[name] = indicator.value
        return out
