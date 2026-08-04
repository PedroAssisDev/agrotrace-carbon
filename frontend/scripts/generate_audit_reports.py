"""Regenera o snapshot HISTÓRICO da auditoria do Capítulo 5 a partir de regressao.json.

Saída em docs/audits/archive/2026-08-03-capitulo-5/final/. Este é um artefato
histórico preservado para rastreabilidade; a auditoria atual vive em
docs/audits/current/ (ver docs/audits/current/_gen_reports.py).

Contagens de status são DERIVADAS automaticamente — sem edição manual.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
_ARCHIVE = REPO / "docs" / "audits" / "archive" / "2026-08-03-capitulo-5"
DEFAULT_MAP = _ARCHIVE / "requirements_map.yaml"
DEFAULT_REG = _ARCHIVE / "final" / "regressao.json"
OUT_DIR = _ARCHIVE / "final"


def _load_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except Exception:
        # Minimal fallback parser for our simple structure
        return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> dict:
    """Very small YAML subset parser for this map file."""
    # Prefer json if someone converted; otherwise use regex extraction
    groups: dict[str, list] = {"RF": [], "RNF": [], "RN": [], "CE": []}
    current_group = None
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        if re.match(r"^  [A-Z]+:\s*$", line):
            if current and current_group:
                groups[current_group].append(current)
                current = None
            current_group = line.strip().rstrip(":")
            continue
        m = re.match(r"^    - id: (\S+)", line)
        if m:
            if current and current_group:
                groups[current_group].append(current)
            current = {"id": m.group(1), "tests": [], "title": "", "static": "", "visual": None}
            continue
        if current is None:
            continue
        if line.strip().startswith("title:"):
            current["title"] = line.split(":", 1)[1].strip()
        elif line.strip().startswith("static:"):
            current["static"] = line.split(":", 1)[1].strip()
        elif line.strip().startswith("visual:"):
            val = line.split(":", 1)[1].strip()
            current["visual"] = None if val in ("null", "~", "") else val
        elif line.strip().startswith("tests:"):
            inner = line.split(":", 1)[1].strip()
            current["tests"] = re.findall(r"([A-Za-z0-9_\-]+)", inner)
    if current and current_group:
        groups[current_group].append(current)
    return {"groups": groups}


def _index_results(reg: dict) -> dict[str, dict]:
    out = {}
    for r in reg.get("results") or []:
        out[str(r.get("name"))] = r
    return out


def _status_for(item: dict, by_name: dict[str, dict]) -> tuple[str, str, list[str]]:
    """Return (status, confidence, evidence_tests)."""
    tests = item.get("tests") or []
    if not tests:
        return "NV", "baixa", []
    outcomes = []
    for t in tests:
        # match exact or prefix (validate_*)
        hit = by_name.get(t)
        if hit is None:
            # try stem matches
            for name, r in by_name.items():
                if name == t or name.startswith(t) or t in name:
                    hit = r
                    break
        if hit is None:
            outcomes.append(None)
        else:
            outcomes.append(hit.get("exit_code"))
    if all(o == 0 for o in outcomes if o is not None) and any(o == 0 for o in outcomes):
        if any(o is None for o in outcomes):
            return "P", "média", [t for t in tests]
        return "A", "alta", [t for t in tests]
    if any(o == 0 for o in outcomes):
        return "P", "média", [t for t in tests]
    if all(o is None for o in outcomes):
        return "NV", "baixa", [t for t in tests]
    return "N", "alta", [t for t in tests]


def generate(reg_path: Path, map_path: Path, out_dir: Path) -> dict[str, Any]:
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    req_map = _load_yaml(map_path)
    by_name = _index_results(reg)
    groups = req_map.get("groups") or {}

    matrix: dict[str, list[dict]] = {}
    counts: dict[str, Counter] = {}
    for gname, items in groups.items():
        rows = []
        c = Counter()
        for item in items:
            status, conf, tests = _status_for(item, by_name)
            c[status] += 1
            rows.append({
                "id": item["id"],
                "title": item.get("title"),
                "status": status,
                "confidence": conf,
                "static": item.get("static"),
                "tests": tests,
                "visual": item.get("visual"),
                "limitation": None if status == "A" else "ver comandos-e-resultados / falhas declaradas",
            })
        matrix[gname] = rows
        counts[gname] = c

    out_dir.mkdir(parents=True, exist_ok=True)

    # matriz
    lines = [
        "# Matriz de rastreabilidade (recomputada)",
        "",
        f"Gerada em: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Legenda: A=Atendido · P=Parcial · N=Não atendido · NV=Não verificável",
        "",
        "## Contagens por grupo (não agregadas)",
        "",
    ]
    for gname, c in counts.items():
        total = sum(c.values())
        lines.append(f"### {gname} (total={total})")
        lines.append("")
        lines.append("| Status | Qtd |")
        lines.append("|--------|-----|")
        for k in ("A", "P", "N", "NV", "NA"):
            lines.append(f"| {k} | {c.get(k, 0)} |")
        lines.append("")
    for gname, rows in matrix.items():
        lines.append(f"## {gname}")
        lines.append("")
        lines.append("| ID | Requisito | Status | Confiança | Evidência estática | Teste executado | Evidência visual | Limitação |")
        lines.append("|----|-----------|--------|-----------|--------------------|-----------------|------------------|-----------|")
        for r in rows:
            lines.append(
                f"| {r['id']} | {r['title']} | {r['status']} | {r['confidence']} | "
                f"{r['static']} | {', '.join(r['tests'])} | {r['visual'] or '—'} | {r['limitation'] or '—'} |"
            )
        lines.append("")
    (out_dir / "matriz-rastreabilidade.md").write_text("\n".join(lines), encoding="utf-8")

    # comandos
    cmd_lines = [
        "# Comandos e resultados (regressão final)",
        "",
        f"Gerada em: {reg.get('generated_at_utc')}",
        f"Python: {reg.get('python', '')[:80]}",
        f"Git commit: {(reg.get('git') or {}).get('commit') or 'sem commits / não identificado'}",
        "",
        "| # | Suite | Exit | Resultado | Tempo (ms) |",
        "|---|-------|------|-----------|------------|",
    ]
    for i, r in enumerate(reg.get("results") or [], start=1):
        cmd_lines.append(
            f"| {i} | {r.get('name')} | {r.get('exit_code')} | {(r.get('summary') or '')[:80].replace('|','/')} | {r.get('duration_ms')} |"
        )
    cmd_lines.append("")
    cmd_lines.append(f"PASS={reg.get('pass_count')} FAIL={reg.get('fail_count')}")
    (out_dir / "comandos-e-resultados.md").write_text("\n".join(cmd_lines), encoding="utf-8")

    # pendencias
    fails = [r for r in (reg.get("results") or []) if r.get("exit_code") not in (0, None)]
    pend = [
        "# Pendências remanescentes (pós-regressão)",
        "",
        f"Falhas declaradas: {len(fails)}",
        "",
    ]
    for r in fails:
        pend.append(f"- **{r.get('name')}** exit={r.get('exit_code')}: {(r.get('summary') or '')[:200]}")
    if not fails:
        pend.append("- Nenhuma falha de comando na regressão (pendências de evidência visual podem permanecer).")
    (out_dir / "pendencias.md").write_text("\n".join(pend), encoding="utf-8")

    # relatorio completo curto
    rel = [
        "# Relatório completo — regressão final",
        "",
        f"Gerado: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Ambiente",
        "",
        f"- Python: `{reg.get('python', '')[:100]}`",
        f"- Commit: `{(reg.get('git') or {}).get('commit') or 'N/A (branch sem commits)'}`",
        f"- Data root isolado: `{reg.get('data_root')}`",
        "",
        "## Resumo de testes",
        "",
        f"- PASS: {reg.get('pass_count')}",
        f"- FAIL: {reg.get('fail_count')}",
        "",
        "## Matriz (contagens por grupo)",
        "",
    ]
    for gname, c in counts.items():
        rel.append(f"- **{gname}**: A={c.get('A',0)} P={c.get('P',0)} N={c.get('N',0)} NV={c.get('NV',0)}")
    rel.append("")
    rel.append("Ver `matriz-rastreabilidade.md`, `comandos-e-resultados.md`, `pendencias.md`.")
    rel.append("")
    rel.append("## Inventário")
    rel.append("")
    rel.append(f"- Antes: `{json.dumps(reg.get('inventory_before'))}`")
    rel.append(f"- Depois: `{json.dumps(reg.get('inventory_after'))}`")
    (out_dir / "relatorio-completo.md").write_text("\n".join(rel), encoding="utf-8")

    # copy inventories
    (out_dir / "_inventory_before.json").write_text(
        json.dumps(reg.get("inventory_before"), indent=2), encoding="utf-8"
    )
    (out_dir / "_inventory_after.json").write_text(
        json.dumps(reg.get("inventory_after"), indent=2), encoding="utf-8"
    )

    summary = {
        "counts": {k: dict(v) for k, v in counts.items()},
        "fail_count": reg.get("fail_count"),
        "pass_count": reg.get("pass_count"),
    }
    (out_dir / "matrix_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reg", type=Path, default=DEFAULT_REG)
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    if not args.reg.exists():
        print(f"regressao.json ausente: {args.reg}")
        return 1
    summary = generate(args.reg, args.map, args.out)
    print("Reports written to", args.out)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
