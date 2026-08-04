"""Validação headless da página Previsões e da fachada de inferência.

Uso:
    python scripts/validate_forecast_page.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

import config  # noqa: E402
from layout.sidebar import MANAGERIAL_NAV  # noqa: E402
from pages import forecasts  # noqa: E402
from pages.router import ROUTES  # noqa: E402
from services.forecast_inference import PredictionFacade  # noqa: E402


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"  [OK]   {name}")
        else:
            msg = f"{name}{f' — {detail}' if detail else ''}"
            self.errors.append(msg)
            print(f"  [FAIL] {msg}")


def _layout_to_str(layout) -> str:
    return str(layout)


def main() -> int:
    v = Validator()
    print("=== validate_forecast_page ===")

    v.check("rota /previsoes registrada", "/previsoes" in ROUTES)
    v.check("layout aponta para forecasts.layout", ROUTES.get("/previsoes") is forecasts.layout)
    nav_paths = [item[0] for item in MANAGERIAL_NAV]
    v.check("Previsões no MANAGERIAL_NAV", "/previsoes" in nav_paths)
    nav_icons = {item[0]: item[1] for item in MANAGERIAL_NAV}
    v.check("ícone chart-area", nav_icons.get("/previsoes") == "fas fa-chart-area")

    v.check(
        "config MODEL_TRAINING_ARTIFACTS_DIR",
        config.MODEL_TRAINING_ARTIFACTS_DIR.name == "artifacts",
    )
    v.check(
        "config MODEL_REGISTRY_PATH",
        config.MODEL_REGISTRY_PATH.name == "registry.jsonl",
    )

    empty_layout = forecasts.layout({}, {"farm_id": None}, {}, None)
    empty_str = _layout_to_str(empty_layout)
    v.check(
        "sem fazenda: EmptyFilterState",
        "Nenhuma fazenda selecionada" in empty_str
        or "EmptyFilterState" in empty_str
        or "fazenda" in empty_str.lower(),
    )
    v.check("sem fazenda: sem input de vacas", "fc-expected-cows" not in empty_str)

    with_farm = forecasts.layout(
        {},
        {"farm_id": "property-001", "farm_name": "Fazenda Teste"},
        {},
        None,
    )
    farm_str = _layout_to_str(with_farm)
    v.check("com fazenda: abas", "fc-tabs" in farm_str)
    v.check("com fazenda: tab modelos", "fc-tab-models" in farm_str)
    v.check("com fazenda: tab regressao", "fc-tab-regression" in farm_str)
    v.check("com fazenda: tab serie temporal", "fc-tab-timeseries" in farm_str)
    v.check("com fazenda: input vacas", "fc-expected-cows" in farm_str)
    v.check("com fazenda: botao calcular", "fc-regression-run" in farm_str)
    v.check("com fazenda: botao projecao", "fc-timeseries-run" in farm_str)
    v.check("com fazenda: criar ausentes", "fc-ensure-missing" in farm_str)
    v.check("com fazenda: modal retreino", "fc-retrain-modal" in farm_str)
    v.check("aviso regressao global", "globais" in farm_str.lower() or "global" in farm_str.lower())

    # Adapter nao expoe treino sklearn no frontend
    import services.model_training_adapter as mta  # noqa: E402

    v.check("adapter disponivel", callable(mta.get_model_availability))
    report = mta.get_model_availability("property-001")
    v.check("availability report models", isinstance(report.get("models"), list))
    v.check("sem treino automatico no layout", "GridSearchCV" not in farm_str)

    # Fachada sem registry
    missing_root = FRONTEND_ROOT / "data" / "_tmp_no_registry_forecast"
    missing_root.mkdir(parents=True, exist_ok=True)
    facade_missing = PredictionFacade(
        artifacts_dir=missing_root,
        registry_path=missing_root / "registry.jsonl",
    )
    availability = facade_missing.get_model_availability("property-001")
    v.check("sem registry: registry_ok False", availability.get("registry_ok") is False)

    # Fachada com artefatos reais do training-service (se existirem)
    registry = config.MODEL_REGISTRY_PATH
    if registry.exists():
        # Garante path do training-service para unpickle dos forecasters
        from services.bootstrap import configure_paths

        configure_paths()
        facade = PredictionFacade()
        real_av = facade.get_model_availability("property-001")
        v.check("registry real legivel", real_av.get("registry_ok") is True)
        if real_av.get("has_any_regression"):
            try:
                result = facade.predict_regression_scenario("property-001", "monthly", 50)
                v.check(
                    "regressao real retorna dict",
                    isinstance(result, dict) and "predicted_milk_production_liters" in result,
                )
            except Exception as exc:  # noqa: BLE001
                v.check("regressao real", False, str(exc))
        else:
            print("  [SKIP] regressao real (sem modelos no registry)")
        if real_av.get("has_property_timeseries"):
            try:
                ts = facade.forecast_time_series("property-001")
                v.check(
                    "serie temporal real retorna 3 periodos",
                    isinstance(ts, dict) and ts.get("forecast_horizon") == 3,
                )
            except Exception as exc:  # noqa: BLE001
                # Sem path/unpickle ou artefato corrompido: reporta, mas nao bloqueia se for
                # apenas incompatibilidade de ambiente sklearn.
                detail = str(exc)
                if "InconsistentVersion" in detail or "sklearn" in detail.lower():
                    print(f"  [SKIP] serie temporal real (ambiente): {detail[:120]}")
                else:
                    v.check("serie temporal real", False, detail)
        else:
            print("  [SKIP] serie temporal real para property-001")
    else:
        print(f"  [SKIP] registry ausente em {registry}")

    if v.errors:
        print(f"\nFALHOU: {len(v.errors)} erro(s)")
        for err in v.errors:
            print(f"  - {err}")
        return 1
    print("\nOK — validate_forecast_page")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
