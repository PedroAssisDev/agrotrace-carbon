"""Validação de SQL read-only para consultas de proveniência na Auditoria Técnica."""

from __future__ import annotations

import re
from dataclasses import dataclass

ALLOWED_TABLE_PREFIXES: tuple[str, ...] = (
    "pipeline_",
    "prov_core_",
    "semantic_",
    "calculation_",
    "audit_",
    "reporting_",
)

FORBIDDEN_KEYWORDS: frozenset[str] = frozenset({
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "REPLACE", "MERGE", "GRANT", "REVOKE", "VACUUM", "ATTACH", "DETACH",
    "PRAGMA", "EXEC", "EXECUTE", "CALL", "COPY", "INTO",
})

DEFAULT_MAX_ROWS = 500


@dataclass
class ValidationResult:
    ok: bool
    sql: str
    error: str | None = None
    tables: list[str] | None = None


def _strip_comments(sql: str) -> str:
    """Remove comentários SQL para inspeção (não altera o SQL executado)."""
    out: list[str] = []
    i = 0
    n = len(sql)
    in_single = False
    in_double = False
    while i < n:
        ch = sql[i]
        if in_single:
            out.append(ch)
            if ch == "'" and i + 1 < n and sql[i + 1] == "'":
                out.append(sql[i + 1])
                i += 2
                continue
            if ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            out.append(ch)
            if ch == '"':
                in_double = False
            i += 1
            continue
        if ch == "'":
            in_single = True
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_double = True
            out.append(ch)
            i += 1
            continue
        if ch == "-" and i + 1 < n and sql[i + 1] == "-":
            while i < n and sql[i] != "\n":
                i += 1
            out.append(" ")
            continue
        if ch == "/" and i + 1 < n and sql[i + 1] == "*":
            i += 2
            while i + 1 < n and not (sql[i] == "*" and sql[i + 1] == "/"):
                i += 1
            i = min(i + 2, n)
            out.append(" ")
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _has_multiple_statements(sql: str) -> bool:
    stripped = sql.strip().rstrip(";")
    if ";" in stripped:
        return True
    return False


def _extract_cte_names(sql_inspected: str) -> set[str]:
    """Nomes de CTEs definidos em WITH ... AS (...)."""
    if not sql_inspected.strip().upper().startswith("WITH"):
        return set()
    names: set[str] = set()
    for match in re.finditer(
        r"(?:\bWITH|,)\s+([a-zA-Z_][\w]*)\s+AS\s*\(",
        sql_inspected,
        re.IGNORECASE,
    ):
        names.add(match.group(1).lower())
    return names


def _extract_tables(sql_inspected: str) -> list[str]:
    """Extrai nomes de tabelas de FROM/JOIN (heurística simples)."""
    cte_names = _extract_cte_names(sql_inspected)
    pattern = re.compile(
        r"(?:FROM|JOIN)\s+([a-zA-Z_][\w]*)",
        re.IGNORECASE,
    )
    tables: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(sql_inspected):
        name = match.group(1)
        key = name.lower()
        if key in cte_names:
            continue
        if key not in seen:
            seen.add(key)
            tables.append(name)
    return tables


def _table_allowed(name: str, allowed_tables: set[str] | None) -> bool:
    lower = name.lower()
    if allowed_tables is not None:
        return lower in allowed_tables
    return any(lower.startswith(p) for p in ALLOWED_TABLE_PREFIXES)


def _enforce_limit(sql: str, limit: int, max_rows: int) -> tuple[str, bool]:
    """Garante LIMIT <= max_rows; adiciona LIMIT se ausente."""
    effective = min(max(1, limit), max_rows)
    inspected = _strip_comments(sql)
    match = re.search(r"\bLIMIT\s+(\d+)", inspected, re.IGNORECASE)
    if match:
        current = int(match.group(1))
        if current > max_rows:
            return re.sub(
                r"\bLIMIT\s+\d+",
                f"LIMIT {effective}",
                sql,
                count=1,
                flags=re.IGNORECASE,
            ), True
        return sql, False
    stripped = sql.rstrip().rstrip(";")
    return f"{stripped}\nLIMIT {effective}", True


def validate_provenance_sql(
    sql: str,
    *,
    limit: int = 100,
    max_rows: int = DEFAULT_MAX_ROWS,
    allowed_tables: set[str] | None = None,
) -> ValidationResult:
    """Valida SQL antes da execução read-only."""
    if not sql or not sql.strip():
        return ValidationResult(False, sql, "Consulta vazia.")

    if _has_multiple_statements(sql):
        return ValidationResult(
            False,
            sql,
            "Consulta bloqueada: múltiplas instruções não são permitidas.",
        )

    inspected = _strip_comments(sql).strip()
    upper = inspected.upper()

    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return ValidationResult(
            False,
            sql,
            "Consulta bloqueada: somente SELECT ou WITH são permitidos.",
        )

    tokens = set(re.findall(r"\b[A-Z_][A-Z0-9_]*\b", upper))
    blocked = tokens & FORBIDDEN_KEYWORDS
    if blocked:
        return ValidationResult(
            False,
            sql,
            "Consulta bloqueada: comandos de alteração de dados não são permitidos nesta seção.",
        )

    tables = _extract_tables(inspected)
    for table in tables:
        if not _table_allowed(table, allowed_tables):
            return ValidationResult(
                False,
                sql,
                f"Consulta bloqueada: tabela '{table}' fora do escopo de auditoria.",
            )

    final_sql, _ = _enforce_limit(sql, limit, max_rows)
    return ValidationResult(True, final_sql, tables=tables)


def format_sql_simple(sql: str) -> str:
    """Formatação leve: keywords em linhas separadas."""
    if not sql:
        return ""
    keywords = (
        "SELECT", "FROM", "WHERE", "JOIN", "LEFT JOIN", "RIGHT JOIN",
        "INNER JOIN", "GROUP BY", "ORDER BY", "HAVING", "LIMIT", "WITH",
    )
    result = sql.strip()
    for kw in sorted(keywords, key=len, reverse=True):
        result = re.sub(
            rf"\b{kw}\b",
            f"\n{kw}",
            result,
            flags=re.IGNORECASE,
        )
    lines = [ln.strip() for ln in result.splitlines() if ln.strip()]
    return "\n".join(lines)
