"""Resultado completo de um ciclo de cálculo de emissões."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from emissions.explanation import CalculationExplanation, build_calculation_explanation
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
    explanation: CalculationExplanation | None = None

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

    def to_explanation_dict(self) -> dict[str, Any] | None:
        """Serializa a explicação canônica (RF009), se presente."""
        if self.explanation is None:
            return None
        return self.explanation.to_dict()

    def attach_explanation(
        self,
        *,
        inputs: Mapping[str, Any],
        factors_used: Mapping[str, Any],
        gwp: Mapping[str, float],
        methodology_label: str = "IPCC/IDF-compatible",
        period: str | None = None,
        temporal_granularity: str | None = None,
        **kwargs: Any,
    ) -> CalculationBundle:
        """Retorna cópia do bundle com ``explanation`` preenchida."""
        from dataclasses import replace

        prov = self.provenance
        expl = build_calculation_explanation(
            flat=self.to_flat_dict(),
            inputs=inputs,
            factors_used=factors_used,
            gwp=gwp,
            method_code=prov.method_code if prov else "ECOFARM-T1-DAIRY",
            method_version=prov.method_version if prov else "1.0.0",
            implementation_version=prov.implementation_version if prov else "0.3.1",
            methodology_label=methodology_label,
            temporal_granularity=temporal_granularity or (
                self.enteric.temporal_scope.value
                if hasattr(self.enteric.temporal_scope, "value")
                else str(self.enteric.temporal_scope)
            ),
            period=period,
            days_in_period=inputs.get("days_in_period"),
            computed_at=prov.computed_at if prov else None,
            **kwargs,
        )
        return replace(self, explanation=expl)
