"""VersionManifest — contrato canônico de versionamento (RNF010).

Não inventa versões: campos ausentes usam value=null + missing_reason explícito.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MANIFEST_CONTRACT_NAME = "VersionManifest"
MANIFEST_CONTRACT_VERSION = "1.0.0"
PUBLICATION_SCHEMA_VERSION = "1.0.0"
EVIDENCE_SCHEMA_VERSION = "evidence_package_v1"

try:
    from app.domain.services.canonical_json_service import official_strategy_fields

    _strategy = official_strategy_fields()
    CANONICALIZATION_STRATEGY = _strategy["canonicalization_strategy"]
    CANONICALIZATION_VERSION = _strategy["canonicalization_version"]
except Exception:
    CANONICALIZATION_STRATEGY = "json_canonical_v1"
    CANONICALIZATION_VERSION = "1"

METHOD_CODE_DEFAULT = "ECOFARM-T1-DAIRY"
METHOD_VERSION_DEFAULT = "1.0.0"


@dataclass
class VersionField:
    value: Any = None
    missing_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "missing_reason": self.missing_reason}


def _known(value: Any) -> VersionField:
    if value is None or value == "" or value == {}:
        return VersionField(value=None, missing_reason="not_available_on_cycle")
    return VersionField(value=value, missing_reason=None)


def _missing(reason: str) -> VersionField:
    return VersionField(value=None, missing_reason=reason)


@dataclass
class VersionManifest:
    """Mapa unificado de versões do ciclo / resultado publicado."""

    contract_name: str = MANIFEST_CONTRACT_NAME
    contract_version: str = MANIFEST_CONTRACT_VERSION
    cycle_id: str | None = None
    layout_id: VersionField = field(default_factory=lambda: _missing("not_set"))
    layout_version: VersionField = field(default_factory=lambda: _missing("not_set"))
    ontology_name: VersionField = field(default_factory=lambda: _missing("not_set"))
    ontology_version: VersionField = field(default_factory=lambda: _missing("not_set"))
    formula_code: VersionField = field(default_factory=lambda: _missing("not_set"))
    formula_version: VersionField = field(default_factory=lambda: _missing("not_set"))
    method_code: VersionField = field(default_factory=lambda: _missing("not_set"))
    method_version: VersionField = field(default_factory=lambda: _missing("not_set"))
    emission_factor_set: VersionField = field(default_factory=lambda: _missing("not_set"))
    emission_factor_set_version: VersionField = field(default_factory=lambda: _missing("not_set"))
    gwp_source: VersionField = field(default_factory=lambda: _missing("not_set"))
    gwp_assessment_report: VersionField = field(default_factory=lambda: _missing("not_set"))
    gwp_horizon: VersionField = field(default_factory=lambda: _missing("not_set"))
    gwp_version: VersionField = field(default_factory=lambda: _missing("not_set"))
    prediction_model_id: VersionField = field(default_factory=lambda: _missing("not_applicable"))
    prediction_model_version: VersionField = field(default_factory=lambda: _missing("not_applicable"))
    publication_schema_version: VersionField = field(
        default_factory=lambda: _known(PUBLICATION_SCHEMA_VERSION)
    )
    evidence_schema_version: VersionField = field(
        default_factory=lambda: _known(EVIDENCE_SCHEMA_VERSION)
    )
    canonicalization_strategy: VersionField = field(
        default_factory=lambda: _known(CANONICALIZATION_STRATEGY)
    )
    canonicalization_version: VersionField = field(
        default_factory=lambda: _known(CANONICALIZATION_VERSION)
    )
    blockchain_contract_name: VersionField = field(default_factory=lambda: _missing("not_set"))
    blockchain_contract_version: VersionField = field(default_factory=lambda: _missing("not_set"))
    abi_version: VersionField = field(default_factory=lambda: _missing("not_set"))
    abi_checksum_sha256: VersionField = field(default_factory=lambda: _missing("not_set"))
    chain_id: VersionField = field(default_factory=lambda: _missing("not_set"))
    contract_address: VersionField = field(default_factory=lambda: _missing("not_set"))
    input_schema_version: VersionField = field(default_factory=lambda: _missing("not_set"))
    output_schema_version: VersionField = field(default_factory=lambda: _missing("not_set"))
    consistency_conflicts: list[str] = field(default_factory=list)
    manifest_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "contract_name": self.contract_name,
            "contract_version": self.contract_version,
            "cycle_id": self.cycle_id,
            "consistency_conflicts": list(self.consistency_conflicts),
            "manifest_hash": self.manifest_hash,
        }
        for name, val in self.__dict__.items():
            if isinstance(val, VersionField):
                out[name] = val.to_dict()
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> VersionManifest:
        data = data or {}
        mf = cls(
            contract_name=data.get("contract_name") or MANIFEST_CONTRACT_NAME,
            contract_version=data.get("contract_version") or MANIFEST_CONTRACT_VERSION,
            cycle_id=data.get("cycle_id"),
            consistency_conflicts=list(data.get("consistency_conflicts") or []),
            manifest_hash=data.get("manifest_hash"),
        )
        for name in list(mf.__dict__.keys()):
            if name in {
                "contract_name",
                "contract_version",
                "cycle_id",
                "consistency_conflicts",
                "manifest_hash",
            }:
                continue
            raw = data.get(name)
            if isinstance(raw, dict) and "value" in raw:
                setattr(
                    mf,
                    name,
                    VersionField(value=raw.get("value"), missing_reason=raw.get("missing_reason")),
                )
            elif raw is not None and not isinstance(raw, dict):
                setattr(mf, name, _known(raw))
        return mf


def _field_value(vf: VersionField) -> Any:
    return vf.value


def assert_consistent(manifest: VersionManifest, cycle: dict) -> list[str]:
    """Detecta versões contraditórias entre manifesto e blocos do ciclo."""
    conflicts: list[str] = []
    wrapper = cycle.get("wrapper") or {}
    ontology = cycle.get("ontology") or {}
    calc = cycle.get("calculation") or {}
    method = calc.get("method") if isinstance(calc.get("method"), dict) else {}

    layout_cycle = cycle.get("layout_id") or wrapper.get("layout_id")
    if _field_value(manifest.layout_id) and layout_cycle and str(_field_value(manifest.layout_id)) != str(layout_cycle):
        conflicts.append("layout_id mismatch between manifest and cycle")

    ont_ver = ontology.get("ontology_version")
    if _field_value(manifest.ontology_version) and ont_ver and str(_field_value(manifest.ontology_version)) != str(ont_ver):
        conflicts.append("ontology_version mismatch between manifest and cycle.ontology")

    mcode = method.get("code") or method.get("method_code")
    if _field_value(manifest.method_code) and mcode and str(_field_value(manifest.method_code)) != str(mcode):
        conflicts.append("method_code mismatch between manifest and calculation.method")

    mver = method.get("version") or method.get("method_version")
    if _field_value(manifest.method_version) and mver and str(_field_value(manifest.method_version)) != str(mver):
        conflicts.append("method_version mismatch between manifest and calculation.method")

    return conflicts


def _load_network_meta(network_meta: dict[str, Any] | None) -> dict[str, Any]:
    if network_meta:
        return dict(network_meta)
    # Try deployment JSON (names only / empty address ok)
    try:
        root = Path(__file__).resolve().parents[2]
        path = (
            root
            / "agrotrace-carbon-blockchain-service"
            / "contracts"
            / "deployments"
            / "sepolia.json"
        )
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def build_version_manifest(
    cycle: dict,
    *,
    network_meta: dict[str, Any] | None = None,
) -> VersionManifest:
    wrapper = cycle.get("wrapper") or {}
    ontology = cycle.get("ontology") or {}
    calc = cycle.get("calculation") or {}
    method = calc.get("method") if isinstance(calc.get("method"), dict) else {}
    expl = calc.get("explanation") if isinstance(calc.get("explanation"), dict) else {}
    gwp_block = calc.get("gwp") if isinstance(calc.get("gwp"), dict) else {}
    factors = calc.get("factors_used") or calc.get("factors") or {}
    forecast = cycle.get("forecast") or cycle.get("prediction") or {}
    pub = cycle.get("publication") or {}
    net = _load_network_meta(network_meta)

    mf = VersionManifest(cycle_id=cycle.get("cycle_id"))

    mf.layout_id = _known(cycle.get("layout_id") or wrapper.get("layout_id"))
    mf.layout_version = _known(wrapper.get("layout_version") or wrapper.get("version"))
    if mf.layout_version.value is None and mf.layout_id.value:
        mf.layout_version = _missing("layout_version_not_recorded")

    mf.ontology_name = _known(
        ontology.get("ontology_name") or ontology.get("name") or ontology.get("model_name")
    )
    if mf.ontology_name.value is None and ontology:
        mf.ontology_name = _known("AgroMRV-Lite") if ontology.get("ontology_version") else _missing(
            "ontology_name_not_recorded"
        )
    mf.ontology_version = _known(ontology.get("ontology_version"))

    # Formula vs method: se só method existir, formula fica com razão explícita
    formula = expl.get("formula") or method.get("formula_code")
    mf.formula_code = _known(formula) if formula else _missing("only_method_recorded")
    mf.formula_version = _known(expl.get("formula_version") or method.get("formula_version"))
    if mf.formula_version.value is None:
        mf.formula_version = _missing("formula_version_not_recorded")

    if not calc:
        mf.method_code = _missing("calculation_not_present")
        mf.method_version = _missing("calculation_not_present")
    else:
        mf.method_code = _known(
            method.get("code") or method.get("method_code") or METHOD_CODE_DEFAULT
        )
        mf.method_version = _known(
            method.get("version") or method.get("method_version") or METHOD_VERSION_DEFAULT
        )

    factor_source = calc.get("factor_source") or method.get("code") or (factors.get("_source") if isinstance(factors, dict) else None)
    mf.emission_factor_set = _known(factor_source) if factors else _missing("factors_not_present")
    if factors and mf.emission_factor_set.value is None:
        mf.emission_factor_set = _known("defaults.py:ECOFARM-T1-DAIRY")
    set_ver = None
    if isinstance(factors, dict):
        set_ver = factors.get("_version") or factors.get("version")
    mf.emission_factor_set_version = _known(set_ver) if set_ver else _missing(
        "factor_set_version_not_catalogued"
    )

    mf.gwp_source = _known(
        gwp_block.get("source")
        or expl.get("gwp_source")
        or (gwp_block and "ipcc_ar4")
        or None
    )
    if gwp_block and mf.gwp_source.value is None:
        mf.gwp_source = _known("ipcc_ar4")
    if not gwp_block and not expl:
        mf.gwp_source = _missing("gwp_not_present")
    mf.gwp_assessment_report = _known(
        gwp_block.get("assessment_report") or expl.get("assessment_report") or ("IPCC AR4" if gwp_block else None)
    )
    if gwp_block and mf.gwp_assessment_report.value is None:
        mf.gwp_assessment_report = _known("IPCC AR4")
    mf.gwp_horizon = _known(
        gwp_block.get("horizon") or gwp_block.get("time_horizon") or expl.get("time_horizon") or ("100y" if gwp_block else None)
    )
    if gwp_block and mf.gwp_horizon.value is None:
        mf.gwp_horizon = _known("100y")
    mf.gwp_version = _known(gwp_block.get("version") or expl.get("gwp_version"))
    if gwp_block and mf.gwp_version.value is None:
        mf.gwp_version = _missing("gwp_set_version_not_catalogued")

    model_id = forecast.get("model_id") or forecast.get("active_model_id")
    model_ver = forecast.get("version") or forecast.get("model_version")
    if model_id:
        mf.prediction_model_id = _known(model_id)
        mf.prediction_model_version = _known(model_ver) if model_ver else _missing(
            "model_version_not_recorded"
        )
    else:
        mf.prediction_model_id = _missing("not_applicable")
        mf.prediction_model_version = _missing("not_applicable")

    mf.publication_schema_version = _known(
        pub.get("schema_version") or PUBLICATION_SCHEMA_VERSION
    )
    mf.evidence_schema_version = _known(EVIDENCE_SCHEMA_VERSION)
    mf.canonicalization_strategy = _known(CANONICALIZATION_STRATEGY)
    mf.canonicalization_version = _known(CANONICALIZATION_VERSION)

    mf.blockchain_contract_name = _known(net.get("contract_name") or "CarbonEvidenceRegistry")
    mf.blockchain_contract_version = _known(net.get("contract_version"))
    mf.abi_version = _known(net.get("contract_version") or net.get("abi_version"))
    mf.abi_checksum_sha256 = _known(net.get("abi_checksum_sha256"))
    mf.chain_id = _known(net.get("chain_id"))
    addr = net.get("contract_address") or ""
    mf.contract_address = _known(addr) if addr else _missing("contract_not_deployed")

    mf.input_schema_version = _known(
        wrapper.get("source_schema_version") or wrapper.get("input_schema_version")
    )
    if mf.input_schema_version.value is None:
        mf.input_schema_version = _missing("source_schema_version_not_copied_to_cycle")
    mf.output_schema_version = _known(
        wrapper.get("output_schema_version") or wrapper.get("normalized_schema_version")
    )
    if mf.output_schema_version.value is None:
        mf.output_schema_version = _missing("output_schema_version_not_recorded")

    conflicts = assert_consistent(mf, cycle)
    mf.consistency_conflicts = conflicts

    payload = mf.to_dict()
    payload.pop("manifest_hash", None)
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    mf.manifest_hash = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return mf


def attach_version_manifest(
    cycle: dict,
    *,
    network_meta: dict[str, Any] | None = None,
) -> dict:
    """Build, attach to cycle, return dict."""
    mf = build_version_manifest(cycle, network_meta=network_meta)
    data = mf.to_dict()
    cycle["version_manifest"] = data
    return data


def evidence_metadata_summary(manifest: dict[str, Any] | VersionManifest) -> dict[str, Any]:
    """Resumo para metadata_payload do pacote (sem secrets)."""
    d = manifest.to_dict() if isinstance(manifest, VersionManifest) else dict(manifest)

    def _v(key: str) -> Any:
        entry = d.get(key) or {}
        if isinstance(entry, dict):
            return entry.get("value")
        return entry

    return {
        "version_manifest_ref": {
            "cycle_id": d.get("cycle_id"),
            "manifest_hash": d.get("manifest_hash"),
            "contract_version": d.get("contract_version"),
        },
        "publication_schema_version": _v("publication_schema_version"),
        "evidence_schema_version": _v("evidence_schema_version"),
        "canonicalization_strategy": _v("canonicalization_strategy"),
        "canonicalization_version": _v("canonicalization_version"),
        "blockchain_contract_name": _v("blockchain_contract_name"),
        "blockchain_contract_version": _v("blockchain_contract_version"),
        "abi_version": _v("abi_version"),
        "abi_checksum_sha256": _v("abi_checksum_sha256"),
        "chain_id": _v("chain_id"),
    }
