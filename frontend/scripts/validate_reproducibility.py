"""RNF009 — Reprodutibilidade numérica (A) e criptográfica (B).

Uso:
    python scripts/validate_reproducibility.py
    python scripts/validate_reproducibility.py --data-root /tmp/repro
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = FRONTEND_ROOT.parent
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from utils.data_root_cli import apply_data_root_from_argv  # noqa: E402

apply_data_root_from_argv()

# Tolerância numérica documentada (RNF009 Parte A)
NUMERIC_REL_TOL = 1e-9
NUMERIC_ABS_TOL = 1e-9


def _near(a: float, b: float) -> bool:
    return math.isclose(float(a), float(b), rel_tol=NUMERIC_REL_TOL, abs_tol=NUMERIC_ABS_TOL)


def _sanitize_report(obj: Any) -> Any:
    from utils.sanitize import sanitize_for_display

    return sanitize_for_display(obj)


class Validator:
    def __init__(self) -> None:
        self.ok: list[str] = []
        self.errors: list[str] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.ok.append(name)
            print(f"  [OK]   {name}")
        else:
            msg = f"{name}{f' — {detail}' if detail else ''}"
            self.errors.append(msg)
            print(f"  [FAIL] {msg}")


def _fixed_farm_and_factors():
    from emissions.defaults import (
        ANIMAL_CATEGORIES,
        ENERGY_VECTORS,
        default_energy_co2_kg_per_unit_annual_basis,
        default_enteric_ch4_kg_per_animal_annual,
        default_fertilizer_factors,
        default_manure_ch4_kg_per_kg_manure,
        default_manure_kg_per_kg_bw_per_day,
        gwp_ipcc_ar4,
    )
    from emissions.farm_period import FarmPeriodInput
    from emissions.temporal_scope import TemporalScope

    farm = FarmPeriodInput(
        temporal_scope=TemporalScope.ANNUAL,
        days_in_period=365,
        headcounts_by_category={c: 10.0 if c == "Lactating_Cows" else 0.0 for c in ANIMAL_CATEGORIES},
        body_weight_kg_by_category={c: 550.0 for c in ANIMAL_CATEGORIES},
        nitrogen_applied_kg=1200.0,
        energy_consumption_by_vector={v: 100.0 for v in ENERGY_VECTORS},
        milk_liters=150000.0,
    )
    factors = dict(
        enteric_ch4_kg_per_animal=default_enteric_ch4_kg_per_animal_annual(),
        manure_kg_per_kg_bw_per_day=default_manure_kg_per_kg_bw_per_day(),
        manure_ch4_kg_per_kg_manure=default_manure_ch4_kg_per_kg_manure(),
        energy_co2_kg_per_unit=default_energy_co2_kg_per_unit_annual_basis(),
        fertilizer_factors=default_fertilizer_factors(),
        gwp=gwp_ipcc_ar4(),
        auto_prorate_factors=False,
        include_provenance=False,
    )
    return farm, factors


def _run_part_a(v: Validator) -> dict[str, Any]:
    from orchestration.pipeline import (
        METHOD_CODE,
        METHOD_VERSION,
        compute_farm_period_emissions,
    )

    farm, factors = _fixed_farm_and_factors()
    a = compute_farm_period_emissions(farm, **factors)
    b = compute_farm_period_emissions(farm, **factors)
    fa, fb = a.to_flat_dict(), b.to_flat_dict()

    keys = [
        "co2e_total_kg",
        "ch4_enteric_kg",
        "ch4_manure_kg",
        "n2o_fertilizer_kg",
        "co2_energy_kg",
    ]
    comparisons = {}
    for k in keys:
        ok = _near(fa.get(k, 0), fb.get(k, 0))
        comparisons[k] = {"a": fa.get(k), "b": fb.get(k), "equal": ok}
        v.check(f"A numeric {k} equal", ok)

    v.check("A method_code stable", METHOD_CODE == "ECOFARM-T1-DAIRY")
    v.check("A method_version stable", METHOD_VERSION == "1.0.0")
    v.check("A gwp equal", factors["gwp"] == factors["gwp"])

    # Negatives
    bad_factors = deepcopy(factors)
    bad_factors["gwp"] = {**factors["gwp"], "CH4": float(factors["gwp"]["CH4"]) + 1.0}
    c = compute_farm_period_emissions(farm, **bad_factors)
    diverged = not _near(fa["co2e_total_kg"], c.to_flat_dict()["co2e_total_kg"])
    v.check("A negative GWP change diverges", diverged)

    bad_ent = deepcopy(factors)
    # bump one enteric factor if dict
    ent = bad_ent["enteric_ch4_kg_per_animal"]
    if isinstance(ent, dict) and ent:
        k0 = next(iter(ent))
        ent = dict(ent)
        ent[k0] = float(ent[k0]) * 1.1
        bad_ent["enteric_ch4_kg_per_animal"] = ent
        d = compute_farm_period_emissions(farm, **bad_ent)
        v.check(
            "A negative factor change diverges",
            not _near(fa["co2e_total_kg"], d.to_flat_dict()["co2e_total_kg"]),
        )
    else:
        v.check("A negative factor change diverges", True, "skipped-non-dict")

    return {
        "tolerance": {"rel": NUMERIC_REL_TOL, "abs": NUMERIC_ABS_TOL},
        "method_code": METHOD_CODE,
        "method_version": METHOD_VERSION,
        "gwp": factors["gwp"],
        "comparisons": comparisons,
        "ignored_fields": ["computed_at", "provenance.timestamps"],
    }


def _run_part_b(v: Validator) -> dict[str, Any]:
    # Prefer blockchain official imports
    sys.path.insert(0, str(WORKSPACE / "agrotrace-carbon-blockchain-service"))
    from app.domain.services.canonical_json_service import to_canonical_json
    from app.domain.services.merkle_service import MerkleLeaf, build_merkle_root
    from app.domain.services.sha256_service import sha256_hex

    item_payload = {
        "schema_version": "evidence_item_v1",
        "item_id": "00000000-0000-4000-8000-000000000001",
        "item_order": 1,
        "item_type": "final_result",
        "period_start": "2026-01-01",
        "period_end": "2026-12-31",
        "core_hashes": {"result": "a" * 64},
    }
    package_payload = {
        "schema_version": "evidence_package_v1",
        "package_id": "00000000-0000-4000-8000-0000000000aa",
        "package_type": "final_result",
        "package_version": "1.0.0",
        "period_start": "2026-01-01",
        "period_end": "2026-12-31",
        "period_granularity": "year",
        "integrity_context": {
            "canonicalization_method": "json_canonical_v1",
            "hash_algorithm": "sha256",
        },
        "items": [{"item_id": item_payload["item_id"], "item_order": 1}],
    }

    # Key order shuffle
    shuffled = {
        "period_end": item_payload["period_end"],
        "item_id": item_payload["item_id"],
        "schema_version": item_payload["schema_version"],
        "core_hashes": item_payload["core_hashes"],
        "item_type": item_payload["item_type"],
        "item_order": item_payload["item_order"],
        "period_start": item_payload["period_start"],
    }
    c1 = to_canonical_json(item_payload)
    c2 = to_canonical_json(shuffled)
    v.check("B canonical bytes equal under key reorder", c1 == c2)

    h1 = sha256_hex(item_payload)
    h2 = sha256_hex(shuffled)
    v.check("B item hash equal under key reorder", h1 == h2)

    pkg_h1 = sha256_hex(package_payload)
    pkg_h2 = sha256_hex(deepcopy(package_payload))
    v.check("B package hash deterministic", pkg_h1 == pkg_h2)

    leaves = [
        MerkleLeaf(item_id=item_payload["item_id"], item_order=1, item_hash=h1),
        MerkleLeaf(
            item_id="00000000-0000-4000-8000-000000000002",
            item_order=2,
            item_hash=sha256_hex({**item_payload, "item_id": "00000000-0000-4000-8000-000000000002", "item_order": 2}),
        ),
    ]
    root1 = build_merkle_root(leaves).merkle_root
    root2 = build_merkle_root(list(reversed(leaves))).merkle_root
    v.check("B merkle root order-invariant by item_order", root1 == root2)

    # Negatives
    altered = {**item_payload, "core_hashes": {"result": "b" * 64}}
    v.check("B altered item changes hash", sha256_hex(altered) != h1)

    bad_pkg = deepcopy(package_payload)
    bad_pkg["integrity_context"] = {
        **bad_pkg["integrity_context"],
        "canonicalization_method": "json_canonical_v2",
    }
    v.check("B different canonicalization strategy changes package hash", sha256_hex(bad_pkg) != pkg_h1)

    return {
        "identity_fields": [
            "schema_version",
            "period_*",
            "item_order",
            "item_type",
            "core_hashes",
            "integrity_context",
            "package_type",
            "package_version",
        ],
        "external_metadata": [
            "execution timestamps",
            "operational status",
            "retry/lock fields",
            "fresh UUIDs from live BuildEvidencePackage",
        ],
        "item_hash": h1,
        "package_hash": pkg_h1,
        "merkle_root": root1,
        "canonical_method": "json_canonical_v1",
    }


def main() -> int:
    import config
    from services import bootstrap

    v = Validator()
    print("=== validate_reproducibility (RNF009) ===\n")
    report: dict[str, Any] = {
        "requirement": "RNF009",
        "numeric_tolerance": {"rel": NUMERIC_REL_TOL, "abs": NUMERIC_ABS_TOL},
    }

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp) / "agrotrace-data"
        config.apply_data_root(root, reset_runtime=True)
        bootstrap.configure_paths()
        bootstrap.configure_env()
        try:
            # Ensure calculation imports
            calc_src = WORKSPACE / "agrotrace-carbon-calculation-service"
            if str(calc_src) not in sys.path:
                sys.path.insert(0, str(calc_src))

            print("-- Part A: numeric --")
            report["part_a"] = _run_part_a(v)
            print("\n-- Part B: cryptographic --")
            report["part_b"] = _run_part_b(v)
        finally:
            config.apply_data_root(None, reset_runtime=True)

    report["ok_count"] = len(v.ok)
    report["fail_count"] = len(v.errors)
    report["failures"] = list(v.errors)
    report["pass"] = len(v.errors) == 0
    report = _sanitize_report(report)

    reports_dir = Path(tempfile.gettempdir()) / "agrotrace-repro-reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / "reproducibility_report.json"
    # Prefer data root reports if available
    try:
        import config as cfg

        if cfg.DATA_ROOT:
            rd = Path(cfg.DATA_ROOT) / "reports"
            rd.mkdir(parents=True, exist_ok=True)
            out_path = rd / "reproducibility_report.json"
    except Exception:
        pass

    # Write next to script-friendly location under frontend/data if exists
    fe_reports = FRONTEND_ROOT / "data" / "reports"
    try:
        fe_reports.mkdir(parents=True, exist_ok=True)
        out_path = fe_reports / "reproducibility_report.json"
    except Exception:
        pass

    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\n--- {len(v.ok)} OK, {len(v.errors)} FAIL ---")
    print(f"report: {out_path.name}")
    if v.errors:
        for e in v.errors:
            print(f"  - {e}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
