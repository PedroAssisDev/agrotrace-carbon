"""
Motor de validação — executa regras declaradas no layout (ref + parâmetros).
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from ..contracts import ValidationReport
from . import library as V

logger = logging.getLogger(__name__)


RuleFn = Callable[..., Any]


def _rule_registry() -> dict[str, RuleFn]:
    return {
        "required_fields": lambda row, line_index, report, fields, **_: V.ensure_required_fields(
            row, fields, line_index, report
        ),
        "date_valid": lambda row, line_index, report, field, **_: V.validate_date_field(
            row.get(field), field, line_index, report
        ),
        "non_negative": lambda row, line_index, report, field, **_: V.validate_numeric_non_negative(
            row.get(field), field, line_index, report
        ),
        "first_day_of_month": lambda row, line_index, report, field, **_: V.validate_first_day_of_month(
            row.get("_parsed_date") or row.get(field), line_index, report
        ),
        "lactating_consistency": lambda row, line_index, report, **_: V.validate_lactating_cows_consistency(
            row.get("number_of_lactating_cows"),
            row.get("lactating_cows"),
            line_index,
            report,
        ),
        "dry_consistency": lambda row, line_index, report, **_: V.validate_dry_cows_consistency(
            row.get("number_of_dry_cows"),
            row.get("dry_cows"),
            line_index,
            report,
        ),
        "milk_sales_le_production": lambda row, line_index, report, **_: V.validate_milk_sales_le_production(
            row.get("milk_sales"),
            row.get("milk_production"),
            line_index,
            report,
        ),
        "weight_range_warning": lambda row, line_index, report, field, **_: (
            V.validate_weight_range(row.get(field), field, line_index, report)
            if row.get(field) is not None
            else True
        ),
        "annual_numeric_non_negative": lambda row, line_index, report, fields, **_: V.validate_numeric_fields_non_negative(
            row, fields, line_index, report
        ),
    }


def validation_rule_refs() -> frozenset[str]:
    """Refs registadas no motor (útil para testes de cobertura e documentação)."""
    return frozenset(_rule_registry().keys())


class ValidationEngine:
    """Aplica lista de regras do layout a um registro lógico."""

    def __init__(self) -> None:
        self._rules = _rule_registry()

    def apply(
        self,
        rules: list[dict[str, Any]],
        row: dict[str, Any],
        line_index: int,
        report: ValidationReport,
    ) -> bool:
        """
        Executa regras em ordem. Retorna False se alguma regra obrigatória falhar
        (regras que retornam False em ensure_required_fields ou non_negative com erro).
        """
        ok = True
        for spec in rules:
            ref = spec.get("ref")
            if not ref:
                continue
            fn = self._rules.get(ref)
            if fn is None:
                logger.warning(
                    "Regra de validação desconhecida (ref=%r) — ignorada. Registe o handler em ValidationEngine.",
                    ref,
                )
                continue
            params = {k: v for k, v in spec.items() if k != "ref"}
            result = fn(row=row, line_index=line_index, report=report, **params)
            if ref == "required_fields" and result is False:
                ok = False
            if ref == "date_valid" and result is None:
                ok = False
            if ref == "non_negative" and result is None:
                ok = False
            if ref == "annual_numeric_non_negative" and result is False:
                ok = False
        return ok
