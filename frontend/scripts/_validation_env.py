"""Ambiente isolado e fixtures compartilhados para scripts validate_*.

Uso típico::

    with isolated_data_root() as root:
        cycles = seed_temporal_fixtures()
        ...
"""

from __future__ import annotations

import time
import traceback
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator


@dataclass
class CheckResult:
    """Resumo estruturado de uma verificação."""

    verificacao: str
    resultado: str  # PASS | FAIL
    evidencia: str = ""
    duracao_ms: int = 0
    erro: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CheckCollector:
    """Acumula CheckResult e imprime [OK]/[FAIL] no estilo dos validate_*."""

    results: list[CheckResult] = field(default_factory=list)

    def check(self, name: str, condition: bool, detail: str = "") -> bool:
        started = time.perf_counter()
        ok = bool(condition)
        elapsed = int((time.perf_counter() - started) * 1000)
        if ok:
            print(f"  [OK]   {name}")
            self.results.append(
                CheckResult(verificacao=name, resultado="PASS", evidencia=detail, duracao_ms=elapsed)
            )
        else:
            msg = f"{name}{f' — {detail}' if detail else ''}"
            print(f"  [FAIL] {msg}")
            self.results.append(
                CheckResult(
                    verificacao=name,
                    resultado="FAIL",
                    evidencia=detail,
                    duracao_ms=elapsed,
                    erro=msg,
                )
            )
        return ok

    def run(self, name: str, fn: Callable[[], Any]) -> Any:
        """Executa ``fn`` medindo duração; falha captura a exceção."""
        started = time.perf_counter()
        try:
            value = fn()
            elapsed = int((time.perf_counter() - started) * 1000)
            print(f"  [OK]   {name}")
            self.results.append(
                CheckResult(verificacao=name, resultado="PASS", evidencia=str(value)[:200], duracao_ms=elapsed)
            )
            return value
        except Exception as exc:
            elapsed = int((time.perf_counter() - started) * 1000)
            err = f"{type(exc).__name__}: {exc}"
            print(f"  [FAIL] {name} — {err}")
            self.results.append(
                CheckResult(
                    verificacao=name,
                    resultado="FAIL",
                    evidencia=traceback.format_exc()[-500:],
                    duracao_ms=elapsed,
                    erro=err,
                )
            )
            return None

    @property
    def errors(self) -> list[str]:
        return [r.erro or r.verificacao for r in self.results if r.resultado == "FAIL"]

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.resultado == "PASS")

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if r.resultado == "FAIL")

    def summary_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok_count,
            "fail": self.fail_count,
            "checks": [r.to_dict() for r in self.results],
        }


@contextmanager
def isolated_data_root(*, bootstrap: bool = True) -> Iterator[Path]:
    """TemporaryDirectory + ``config.apply_data_root`` + bootstrap opcional.

    Não toca em ``frontend/data`` operacional. Restaura o root default ao sair.
    """
    import tempfile

    import config
    from utils.data_root_cli import apply_data_root_from_argv

    # Consome --data-root se o chamador passou; caso contrário usa temp.
    explicit = apply_data_root_from_argv()
    own_temp = explicit is None

    if own_temp:
        tmp_cm = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        tmp = tmp_cm.__enter__()
        root = Path(tmp) / "agrotrace-data"
        config.apply_data_root(root, reset_runtime=True)
    else:
        tmp_cm = None
        root = Path(explicit)

    if bootstrap:
        try:
            from services import bootstrap as boot

            boot.configure_paths()
            boot.configure_env()
            boot.init_provenance_db()
            try:
                boot.init_blockchain_db()
            except Exception:
                pass
        except Exception:
            pass
        try:
            from services import provenance_adapter as prov

            prov._recorder = None
            prov._uow_factory = None
            prov._reviewer_agent_id = None
        except Exception:
            pass

    try:
        yield root
    finally:
        try:
            from provenance_service.infrastructure.db.session import get_engine
            from provenance_service.infrastructure.db import clear_engine_cache

            try:
                get_engine().dispose()
            except Exception:
                pass
            clear_engine_cache()
        except Exception:
            pass
        try:
            from services import provenance_adapter as prov

            prov._recorder = None
            prov._uow_factory = None
        except Exception:
            pass
        config.apply_data_root(None, reset_runtime=True)
        if tmp_cm is not None:
            tmp_cm.__exit__(None, None, None)


def _base_cycle(
    *,
    cycle_id: str,
    property_id: str,
    property_name: str,
    reporting_period: str,
    input_granularity: str,
    calc_base: str,
    co2e_kg: float,
    milk_liters: float,
    lot_id: str | None = None,
    status: str = "AWAITING_APPROVAL",
) -> dict[str, Any]:
    """Ciclo mínimo suficiente para filtros/temporal/dashboard."""
    intensity = (co2e_kg / milk_liters) if milk_liters else None
    cycle: dict[str, Any] = {
        "cycle_id": cycle_id,
        "property_id": property_id,
        "farm_id": property_id,
        "property_name": property_name,
        "reporting_period": reporting_period,
        "current_status": status,
        "temporal_coverage": {
            "source_granularity": input_granularity,
            "granularity": calc_base,
            "period_label": reporting_period,
        },
        "calculation": {
            "co2e_total_kg": co2e_kg,
            "milk_production_liters": milk_liters,
            "co2e_intensity_per_milk_liter": intensity,
            "by_source": {"enteric": co2e_kg * 0.6, "manure": co2e_kg * 0.2, "energy": co2e_kg * 0.2},
            "status": "DONE",
        },
        "steps": {
            "ingestion": {"status": "DONE"},
            "normalization": {"status": "DONE"},
            "semantic": {"status": "DONE"},
            "calculation": {"status": "DONE"},
            "approval": {"status": "AWAITING_APPROVAL" if status == "AWAITING_APPROVAL" else "DONE"},
            "publication": {"status": "PENDING"},
        },
        "approval": {"decision": "PENDING" if status == "AWAITING_APPROVAL" else "APPROVED"},
        "seed_fixture": True,
        "pipeline_run_id": f"RUN-{cycle_id}",
    }
    if lot_id:
        cycle["lot_id"] = lot_id
        cycle["organizational_granularity"] = "LOT"
    return cycle


def seed_temporal_fixtures(*, persist: bool = True) -> list[dict[str, Any]]:
    """Cria fixtures determinísticos: annual (5), monthly (12), daily→monthly (6).

    - FARM-ANNUAL-001: 2021..2025 (annual)
    - FARM-MONTHLY-001: Jan/2026..Dec/2026 (monthly)
    - FARM-DAILY-001: Jan/2026..Jun/2026 consolidado mensal a partir de daily

    Não depende do catálogo emulado do save-file nem do ambiente operacional.
    """
    from utils.file_helpers import save_cycle

    cycles: list[dict[str, Any]] = []

    # Annual: 5 years
    for year in range(2021, 2026):
        cycles.append(
            _base_cycle(
                cycle_id=f"ANNUAL-{year}-FARM-ANNUAL-001",
                property_id="FARM-ANNUAL-001",
                property_name="Fazenda Santa Clara Sustentável",
                reporting_period=str(year),
                input_granularity="annual",
                calc_base="annual",
                co2e_kg=1000.0 + (year - 2021) * 50,
                milk_liters=50000.0 + (year - 2021) * 1000,
                lot_id="LOT-A-01",
            )
        )

    # Monthly: 12 months of 2026
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    for month in range(1, 13):
        label = f"{month_names[month - 1]}/2026"
        period = f"2026-{month:02d}"
        cycles.append(
            _base_cycle(
                cycle_id=f"MONTHLY-{period}-FARM-MONTHLY-001",
                property_id="FARM-MONTHLY-001",
                property_name="Fazenda Boa Vista Leiteira",
                reporting_period=period,
                input_granularity="monthly",
                calc_base="monthly",
                co2e_kg=80.0 + month,
                milk_liters=4000.0 + month * 10,
                lot_id="LOT-M-01",
            )
        )
        # Keep period_label hint used by temporal_model validators
        cycles[-1]["temporal_coverage"]["period_label"] = label
        cycles[-1]["period_label"] = label

    # Daily source → monthly consolidated: Jan..Jun 2026 (exactly 6)
    for month in range(1, 7):
        label = f"{month_names[month - 1]}/2026"
        period = f"2026-{month:02d}"
        days_in_month = 31 if month in (1, 3, 5) else 30 if month != 2 else 28
        cycles.append(
            _base_cycle(
                cycle_id=f"MONTHLY-{period}-FARM-DAILY-001",
                property_id="FARM-DAILY-001",
                property_name="Fazenda Experimental Sensorial",
                reporting_period=period,
                input_granularity="daily",
                calc_base="monthly",
                co2e_kg=70.0 + month,
                milk_liters=3500.0 + month * 10,
                lot_id="LOT-D-01",
            )
        )
        cycles[-1]["temporal_coverage"]["period_label"] = label
        cycles[-1]["period_label"] = label
        cycles[-1]["data_entries"] = [
            {"day": d, "milk_liters": 100.0, "co2e_kg": 2.0} for d in range(1, days_in_month + 1)
        ]
        cycles[-1]["organizational_granularity"] = "ANIMAL"
        cycles[-1]["animal_id"] = "ANIMAL-D-001"

    if persist:
        for c in cycles:
            save_cycle(c)
    return cycles


def seed_pending_approval_fixtures(*, persist: bool = True) -> list[dict[str, Any]]:
    """Fixture mínimo para validate_pending_approval_seed: 2 fazendas, N pendentes.

    Contagem derivada do próprio fixture (não assume 17 do ambiente operacional).
    """
    cycles = seed_temporal_fixtures(persist=persist)
    # Apenas monthly + annual entram como "pending seed oficial" neste validador;
    # daily também fica pending mas é contado separadamente.
    return cycles


def print_structured_summary(collector: CheckCollector, title: str) -> int:
    """Imprime resumo e retorna exit code 0/1."""
    print()
    print(f"--- {collector.ok_count} OK, {collector.fail_count} FAIL ---")
    for r in collector.results:
        if r.resultado == "FAIL":
            print(f"  - {r.erro}")
    if collector.fail_count:
        print(f"{title}: FAIL")
        return 1
    print(f"{title}: PASS")
    return 0
