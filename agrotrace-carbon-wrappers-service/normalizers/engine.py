"""
Motor de normalização por layout — extensão plugável do núcleo.

A família do layout (`layout_family` no YAML) escolhe o finalizador registado;
famílias desconhecidas preservam o registo lógico sem chaves internas (`_*`).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Callable

from ..contracts import OrganizationalDescriptor, ValidationIssue, ValidationReport, Severity
from ..core.inference import infer_year_from_source_uri
from ..temporal import interval_for_month, temporal_instant, temporal_interval_month, temporal_interval_year
from .library import finalize_annual_row, finalize_intraday_row, finalize_monthly_row

FamilyFinalizer = Callable[
    [dict[str, Any], frozenset[str], dict[str, Any], int, ValidationReport, dict[str, Any]],
    dict[str, Any] | None,
]


def _finalize_intraday(
    _layout_doc: dict[str, Any],
    _numeric_annual: frozenset[str],
    row: dict[str, Any],
    _line_index: int,
    _report: ValidationReport,
    _options: dict[str, Any],
) -> dict[str, Any] | None:
    d = row.get("_parsed_date")
    if d is None:
        return None
    rec = finalize_intraday_row(row)
    if not rec:
        return None
    animal_id = rec.get("animal_id") or ""
    rec["_temporal_context"] = temporal_instant(d).to_dict()
    rec["_organizational_context"] = OrganizationalDescriptor(
        granularity="animal",
        identifier=str(animal_id),
    ).to_dict()
    return rec


def _finalize_monthly(
    _layout_doc: dict[str, Any],
    _numeric_annual: frozenset[str],
    row: dict[str, Any],
    _line_index: int,
    _report: ValidationReport,
    _options: dict[str, Any],
) -> dict[str, Any] | None:
    d = row.get("_parsed_date")
    if d is None or not isinstance(d, date):
        return None
    p_start, p_end = interval_for_month(d)
    rec = finalize_monthly_row(row, d, p_end)
    pid = (rec.get("property_id") or "").strip()
    rec["_temporal_context"] = temporal_interval_month(d).to_dict()
    rec["_organizational_context"] = OrganizationalDescriptor(
        granularity="property",
        identifier=pid,
    ).to_dict()
    return rec


def _finalize_annual(
    _layout_doc: dict[str, Any],
    numeric_annual: frozenset[str],
    row: dict[str, Any],
    line_index: int,
    report: ValidationReport,
    options: dict[str, Any],
) -> dict[str, Any] | None:
    year = options.get("year") or infer_year_from_source_uri(options.get("source_uri", ""))
    if year is None:
        report.add_warning(
            ValidationIssue(
                code="missing_year",
                message="Ano não informado; usando ano UTC atual como fallback",
                severity=Severity.WARNING,
                field=None,
                line_index=line_index,
            )
        )
        year = datetime.now(UTC).year
    rec = finalize_annual_row(row, int(year), numeric_annual)
    pname = (rec.get("property_name") or "").strip()
    rec["_temporal_context"] = temporal_interval_year(int(year)).to_dict()
    rec["_organizational_context"] = OrganizationalDescriptor(
        granularity="property",
        identifier=pname,
    ).to_dict()
    return rec


def _finalize_generic(
    _layout_doc: dict[str, Any],
    _numeric_annual: frozenset[str],
    row: dict[str, Any],
    _line_index: int,
    _report: ValidationReport,
    _options: dict[str, Any],
) -> dict[str, Any] | None:
    return {k: v for k, v in row.items() if not k.startswith("_")}


_FAMILY_FINALIZERS: dict[str, FamilyFinalizer] = {
    "intraday": _finalize_intraday,
    "monthly": _finalize_monthly,
    "annual": _finalize_annual,
}


class NormalizationEngine:
    """Normalização pós-validação (tipos, contexto temporal/organizacional por família)."""

    def __init__(self, layout_doc: dict[str, Any], *, numeric_annual: frozenset[str]) -> None:
        self._doc = layout_doc
        self._family = str(layout_doc.get("layout_family") or "")
        self._numeric_annual = numeric_annual
        self._finalizer = _FAMILY_FINALIZERS.get(self._family, _finalize_generic)

    def finalize_record(
        self,
        row: dict[str, Any],
        line_index: int,
        report: ValidationReport,
        options: dict[str, Any],
    ) -> dict[str, Any] | None:
        return self._finalizer(self._doc, self._numeric_annual, row, line_index, report, options)

    @staticmethod
    def register_family_finalizer(family: str, fn: FamilyFinalizer) -> None:
        """Regista ou substitui o finalizador para uma família (extensão em tempo de arranque / testes)."""
        _FAMILY_FINALIZERS[family] = fn
