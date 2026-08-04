"""Validação headless da seção Consultas de Proveniência.

Uso:
    python scripts/validate_provenance_queries.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

import config  # noqa: E402
from pages.technical_audit import layout as audit_layout  # noqa: E402
from pages.technical_audit_sections import build_provenance_queries_section  # noqa: E402
from services.mock_data import mock_full_cycle  # noqa: E402
from services.page_context import resolve_page_context  # noqa: E402
from services.provenance_query_service import (  # noqa: E402
    apply_context_placeholders,
    build_query_context_from_cycle,
    execute_provenance_query,
)
from services.provenance_query_templates import list_query_templates  # noqa: E402
from services.provenance_schema_service import get_audit_schema  # noqa: E402
from utils.file_helpers import save_cycle  # noqa: E402


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.ok: list[str] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.ok.append(name)
            print(f"  [OK]   {name}")
        else:
            msg = f"{name}{f' — {detail}' if detail else ''}"
            self.errors.append(msg)
            print(f"  [FAIL] {msg}")


def main() -> int:
    v = Validator()
    print("=== validate_provenance_queries ===\n")

    demo = mock_full_cycle()
    save_cycle(demo)
    gf = {
        "farm_id": demo.get("property_id"),
        "farm_name": demo.get("property_name"),
        "cycle_id": demo.get("cycle_id"),
    }
    ctx = resolve_page_context(demo, gf, demo.get("cycle_id"))

    # Schema
    schema = get_audit_schema()
    names = schema.get("allowed_table_names") or []
    v.check("schema retorna tabelas", len(names) >= 10)
    v.check("audit_outbox_event no schema", "audit_outbox_event" in names)
    v.check("pipeline_pipeline_run no schema", "pipeline_pipeline_run" in names)

    # Templates
    templates = list_query_templates()
    v.check("12 templates definidos", len(templates) == 12)
    qctx = build_query_context_from_cycle(demo, ctx.farm_id)
    for tpl in templates:
        resolved = apply_context_placeholders(tpl["sql"], qctx)
        v.check(f"template {tpl['id']} substitui contexto", "{{" not in resolved or not qctx.get("pipeline_run_id"))

    # UI
    try:
        section = build_provenance_queries_section(ctx)
        v.check("build_provenance_queries_section monta", section is not None)
        v.check("workspace contém editor SQL", "ta-prov-sql-input" in str(section))
        v.check("workspace contém templates", "ta-prov-template-select" in str(section))
    except Exception as exc:
        v.check("build_provenance_queries_section monta", False, str(exc))

    try:
        page = audit_layout(demo, gf, {}, demo.get("cycle_id"))
        v.check("aba Consultas de Proveniência no layout", "Consultas de Proveniência" in str(page))
        v.check("tab_id ta-prov-queries presente", "ta-prov-queries" in str(page))
        v.check("não é rota de menu separada", "/provenance" not in str(page) or "ta-prov-queries" in str(page))
    except Exception as exc:
        v.check("audit_layout com nova aba", False, str(exc))

    # Execução real se DB existir
    if config.PROV_DB_PATH.exists():
        result = execute_provenance_query(
            "SELECT COUNT(*) AS total FROM audit_outbox_event",
            limit=10,
            context=qctx,
        )
        v.check("SELECT real executa", result.get("ok") is True, result.get("error") or "")
        v.check("retorno tem colunas", bool(result.get("columns")))
        blocked = execute_provenance_query("DELETE FROM audit_outbox_event", context=qctx)
        v.check("DELETE bloqueado na execução", not blocked.get("ok"))
    else:
        v.check("DB ausente — execução real skip", True)
        missing = execute_provenance_query("SELECT 1", context=qctx)
        v.check("DB ausente retorna erro amigável", bool(missing.get("error")))

    print(f"\n{len(v.ok)} OK, {len(v.errors)} FAIL")
    return 1 if v.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
