"""
Validadores reutilizáveis — estrutura, tipo e domínio básico.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from ..contracts import ErrorCode, ValidationIssue, ValidationReport, Severity
from ..temporal import parse_date


def ensure_required_fields(
    row: dict[str, Any],
    required: list[str],
    line_index: int,
    report: ValidationReport,
) -> bool:
    ok = True
    for field_name in required:
        val = row.get(field_name)
        if val is None or (isinstance(val, str) and not val.strip()):
            report.add_error(
                ValidationIssue(
                    code=ErrorCode.MISSING_REQUIRED_FIELD,
                    message=f"Campo obrigatório ausente: {field_name}",
                    severity=Severity.ERROR,
                    field=field_name,
                    line_index=line_index,
                ),
                line_index=line_index,
            )
            ok = False
    return ok


def parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, Decimal):
        return value
    s = str(value).strip().replace(",", ".")
    if not s:
        return None
    try:
        return Decimal(s)
    except Exception:
        return None


def validate_numeric_non_negative(
    value: Any,
    field_name: str,
    line_index: int,
    report: ValidationReport,
) -> Decimal | None:
    n = parse_decimal(value)
    if n is None:
        report.add_error(
            ValidationIssue(
                code=ErrorCode.TYPE_ERROR,
                message=f"Valor não numérico em {field_name}: {value!r}",
                severity=Severity.ERROR,
                field=field_name,
                line_index=line_index,
                value=value,
            ),
            line_index=line_index,
        )
        return None
    if n < 0:
        report.add_error(
            ValidationIssue(
                code=ErrorCode.DOMAIN_VIOLATION,
                message=f"Valor negativo não permitido em {field_name}: {n}",
                severity=Severity.ERROR,
                field=field_name,
                line_index=line_index,
            ),
            line_index=line_index,
        )
        return None
    return n


def validate_date_field(
    value: Any,
    field_name: str,
    line_index: int,
    report: ValidationReport,
) -> Any:
    d = parse_date(value)
    if d is None:
        report.add_error(
            ValidationIssue(
                code=ErrorCode.TYPE_ERROR,
                message=f"Data inválida em {field_name}: {value!r}",
                severity=Severity.ERROR,
                field=field_name,
                line_index=line_index,
                value=value,
            ),
            line_index=line_index,
        )
        return None
    return d


WEIGHT_MIN_KG = 200
WEIGHT_MAX_KG = 900


def validate_weight_range(
    weight_kg: Decimal | float,
    field_name: str,
    line_index: int,
    report: ValidationReport,
) -> bool:
    w = float(weight_kg)
    if w < WEIGHT_MIN_KG or w > WEIGHT_MAX_KG:
        report.add_warning(
            ValidationIssue(
                code=ErrorCode.DOMAIN_VIOLATION,
                message=f"Peso fora da faixa típica (200–900 kg) em {field_name}: {w}",
                severity=Severity.WARNING,
                field=field_name,
                line_index=line_index,
            )
        )
        return False
    return True


def validate_first_day_of_month(d: Any, line_index: int, report: ValidationReport) -> bool:
    from datetime import date

    if not isinstance(d, date):
        return False
    if d.day != 1:
        report.add_warning(
            ValidationIssue(
                code=ErrorCode.DOMAIN_VIOLATION,
                message=f"Period esperado como primeiro dia do mês (YYYY-MM-01); obtido: {d}",
                severity=Severity.WARNING,
                field="period",
                line_index=line_index,
            )
        )
        return False
    return True


def validate_lactating_cows_consistency(
    number_of_lactating: Any,
    lactating_cows: Any,
    line_index: int,
    report: ValidationReport,
) -> None:
    n1 = parse_decimal(number_of_lactating)
    n2 = parse_decimal(lactating_cows)
    if n1 is not None and n2 is not None and n1 != n2:
        report.add_warning(
            ValidationIssue(
                code="schema_consistency",
                message=f"Number_of_Lactating_Cows ({n1}) != Lactating_Cows ({n2})",
                severity=Severity.WARNING,
                field="lactating_cows",
                line_index=line_index,
            )
        )


def validate_dry_cows_consistency(
    number_of_dry: Any,
    dry_cows: Any,
    line_index: int,
    report: ValidationReport,
) -> None:
    n1 = parse_decimal(number_of_dry)
    n2 = parse_decimal(dry_cows)
    if n1 is not None and n2 is not None and n1 != n2:
        report.add_warning(
            ValidationIssue(
                code="schema_consistency",
                message=f"Number_of_Dry_Cows ({n1}) != Dry_Cows ({n2})",
                severity=Severity.WARNING,
                field="dry_cows",
                line_index=line_index,
            )
        )


def validate_milk_sales_le_production(
    milk_sales: Any,
    milk_production: Any,
    line_index: int,
    report: ValidationReport,
) -> None:
    s = parse_decimal(milk_sales)
    p = parse_decimal(milk_production)
    if s is not None and p is not None and s > p:
        report.add_warning(
            ValidationIssue(
                code=ErrorCode.DOMAIN_VIOLATION,
                message=f"Milk_Sales ({s}) > Milk_Production ({p})",
                severity=Severity.WARNING,
                field="milk_sales",
                line_index=line_index,
            )
        )


def validate_numeric_fields_non_negative(
    row: dict[str, Any],
    fields: list[str],
    line_index: int,
    report: ValidationReport,
) -> bool:
    """Valida que campos presentes e numéricos são >= 0 (warning apenas se inválido como número)."""
    ok = True
    for fname in fields:
        if fname not in row or row[fname] is None:
            continue
        v = row[fname]
        if isinstance(v, str) and not v.strip():
            continue
        n = parse_decimal(v)
        if n is None:
            report.add_warning(
                ValidationIssue(
                    code=ErrorCode.TYPE_ERROR,
                    message=f"Valor não numérico em {fname}: {v!r}",
                    severity=Severity.WARNING,
                    field=fname,
                    line_index=line_index,
                )
            )
            ok = False
            continue
        if n < 0:
            report.add_error(
                ValidationIssue(
                    code=ErrorCode.DOMAIN_VIOLATION,
                    message=f"Valor negativo em {fname}: {n}",
                    severity=Severity.ERROR,
                    field=fname,
                    line_index=line_index,
                ),
                line_index=line_index,
            )
            ok = False
    return ok
