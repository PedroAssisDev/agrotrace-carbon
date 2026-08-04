# -*- coding: utf-8 -*-
"""Gera markdown da auditoria a partir de 09-resultados.json e _regressao.json.

Nenhum status, total, hash ou conclusão é hardcoded — tudo deriva dos JSON.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

DEFAULT_DIR = Path(__file__).resolve().parent

STATUS_COLS = (
    "ATENDIDO",
    "PARCIALMENTE ATENDIDO",
    "NÃO ATENDIDO",
    "NÃO VERIFICÁVEL",
    "NÃO APLICÁVEL",
)


def load_inputs(directory: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    res = json.loads((directory / "09-resultados.json").read_text(encoding="utf-8"))
    reg = json.loads((directory / "_regressao.json").read_text(encoding="utf-8"))
    return res, reg


def count_by_status(items: list[dict[str, Any]], *, status_key: str = "status") -> dict[str, int]:
    c: Counter[str] = Counter()
    for it in items:
        st = str(it.get(status_key) or "").strip()
        if st:
            c[st] += 1
    return dict(c)


def validate_counts(resultados: dict[str, Any]) -> None:
    """Garante coerência entre listas e contagens declaradas."""
    cont = resultados.get("contagens") or {}
    checks = [
        ("RF", resultados.get("RF") or [], cont.get("RF") or {}),
        ("RNF", resultados.get("RNF") or [], cont.get("RNF") or {}),
        ("CE", resultados.get("CE") or [], cont.get("CE") or {}),
    ]
    for name, items, declared in checks:
        computed = count_by_status(items)
        if sum(computed.values()) != len(items):
            raise ValueError(f"{name}: soma dos status != len(itens)")
        for st, n in computed.items():
            if int(declared.get(st, 0)) != n:
                raise ValueError(
                    f"{name}: contagens['{st}']={declared.get(st)} != calculado {n}"
                )
        for st, n in declared.items():
            if st == "nota":
                continue
            if int(n) != computed.get(st, 0):
                raise ValueError(
                    f"{name}: contagens declara {st}={n} mas lista tem {computed.get(st, 0)}"
                )

    decisoes = resultados.get("decisoes") or []
    d423, d4510 = split_decisions(decisoes)
    c423 = count_by_status(d423)
    c4510 = count_by_status(d4510)
    declared_423 = cont.get("decisoes_4_2_3") or {}
    declared_4510 = cont.get("decisoes_complementares_4_5_10") or {}
    for st, n in c423.items():
        if int(declared_423.get(st, 0)) != n:
            raise ValueError(f"decisoes_4_2_3: {st} declarado {declared_423.get(st)} != {n}")
    for st, n in c4510.items():
        if int(declared_4510.get(st, 0)) != n:
            raise ValueError(
                f"decisoes_complementares_4_5_10: {st} declarado {declared_4510.get(st)} != {n}"
            )


def split_decisions(
    decisoes: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    d423 = [d for d in decisoes if str(d.get("secao") or "") == "4.2.3"]
    d4510 = [d for d in decisoes if str(d.get("secao") or "") == "4.5.10"]
    return d423, d4510


def _trunc_hash(h: str | None, n: int = 8) -> str:
    if not h:
        return "—"
    h = str(h)
    if len(h) <= n * 2 + 1:
        return h
    return f"{h[:n]}...{h[-n:]}"


def render_db_status(operacional: dict[str, Any] | None) -> str:
    """Tabela de hashes + match true/false/não verificável + nota."""
    if not operacional:
        return (
            "| Arquivo | Antes | Depois | Match |\n"
            "|---------|-------|--------|-------|\n"
            "| *(não verificável)* | — | — | não verificável |\n"
        )

    rows = [
        "| Arquivo | SHA-256 antes | SHA-256 depois | Match |",
        "|---------|---------------|----------------|-------|",
    ]

    def _row(name: str, before_key: str, after_key: str, match_key: str) -> None:
        before = operacional.get(before_key)
        after = operacional.get(after_key)
        if before is None and after is None and match_key not in operacional:
            rows.append(f"| {name} | — | — | não verificável |")
            return
        match = operacional.get(match_key)
        if match is True:
            label = "sim"
        elif match is False:
            label = "não"
        else:
            label = "não verificável"
        rows.append(
            f"| {name} | `{_trunc_hash(before)}` | `{_trunc_hash(after)}` | {label} |"
        )

    _row(
        "blockchain_service.db",
        "blockchain_service.db_sha256_before",
        "blockchain_service.db_sha256_after",
        "blockchain_match",
    )
    _row(
        "provenance.db",
        "provenance.db_sha256_before",
        "provenance.db_sha256_after",
        "provenance_match",
    )

    note = operacional.get("provenance_note") or operacional.get("nota")
    body = "\n".join(rows)
    if note:
        body += f"\n\n**Nota:** {note}\n"
    return body


def _status_table_row(label: str, counts: dict[str, Any], expected_total: int | None = None) -> str:
    cells = [label]
    for st in STATUS_COLS:
        cells.append(str(int(counts.get(st, 0) or 0)))
    return "| " + " | ".join(cells) + " |"


def _git_summary(git: dict[str, Any] | None) -> str:
    git = git or {}
    branch = git.get("branch") or "—"
    commits = git.get("commits")
    head = git.get("head")
    if commits is None:
        commits_txt = "não informado"
    else:
        commits_txt = str(commits)
    head_txt = head if head else "inexistente"
    return f"branch `{branch}`, **{commits_txt} commits**, HEAD: {head_txt}"


def _banks_summary(operacional: dict[str, Any] | None) -> str:
    if not operacional:
        return "estado dos bancos operacionais **não verificável** nesta entrada"
    bc = operacional.get("blockchain_match")
    pv = operacional.get("provenance_match")
    parts = []
    if bc is True:
        parts.append("blockchain_service.db inalterado")
    elif bc is False:
        parts.append("blockchain_service.db **alterado**")
    else:
        parts.append("blockchain_service.db não verificável")
    if pv is True:
        parts.append("provenance.db inalterado")
    elif pv is False:
        parts.append("provenance.db **alterado**")
    else:
        parts.append("provenance.db não verificável")
    note = operacional.get("provenance_note")
    text = "; ".join(parts)
    if note and pv is False:
        text += f". Nota: {note}"
    if bc is True and pv is True:
        return f"hashes SHA-256 inalterados ({text})"
    return text


def _counts_row_label(name: str, n: int) -> str:
    return f"{name} ({n})"


def render_resumo(resultados: dict[str, Any], regressao: dict[str, Any]) -> str:
    aud = resultados.get("auditoria") or {}
    cont = resultados.get("contagens") or {}
    cmd = resultados.get("comandos_resumo") or {}
    operacional = resultados.get("operacional_intact") or {}
    git = aud.get("git") or {}
    d423, d4510 = split_decisions(resultados.get("decisoes") or [])
    rf_n = len(resultados.get("RF") or [])
    rnf_n = len(resultados.get("RNF") or [])
    ce_n = len(resultados.get("CE") or [])

    pass_c = cmd.get("pass_count", regressao.get("pass_count"))
    fail_c = cmd.get("fail_count", regressao.get("fail_count"))
    steps = cmd.get("steps", len(regressao.get("results") or []))
    falhas = cmd.get("falhas") or [
        x.get("name")
        for x in (regressao.get("results") or [])
        if x.get("exit_code") not in (0, None)
    ]
    prontidao = aud.get("prontidao_capitulo_5") or "—"

    rf_c = cont.get("RF") or count_by_status(resultados.get("RF") or [])
    rnf_c = cont.get("RNF") or count_by_status(resultados.get("RNF") or [])
    ce_c = cont.get("CE") or count_by_status(resultados.get("CE") or [])
    dec_c = count_by_status(d423)

    parcial_itens = [
        f"- **{r['id']}:** {r.get('lacunas') or r.get('status')}"
        for r in (resultados.get("RF") or []) + (resultados.get("RNF") or [])
        if "PARCIAL" in str(r.get("status") or "")
    ]
    falhas_txt = ", ".join(f"`{f}`" for f in falhas) if falhas else "nenhuma"

    return f"""# Resumo executivo — auditoria pós-implementação

**Data (UTC):** {aud.get('generated_at_utc') or '—'}  
**Dissertação:** `{aud.get('dissertacao') or '—'}`  
**Git:** {_git_summary(git)}  
**Isolamento:** {(aud.get('ambiente') or {}).get('isolamento') or '—'}  
**Bancos operacionais:** {_banks_summary(operacional)}  

## Conclusão geral

A implementação cobre RF/RNF/decisões/CE conforme as contagens abaixo, com evidência em ambiente isolado ({pass_c}/{steps} passos da regressão; {fail_c} falha(s): {falhas_txt}).  
Decisões oficiais Cap. 4.2.3: **{len(d423)}**; complementar §4.5.10: **{len(d4510)}**.

## Classificação de prontidão (Capítulo 5)

**{prontidao}**

## Contagens (automáticas)

| Grupo | ATENDIDO | PARCIAL | NÃO ATENDIDO | NÃO VERIFICÁVEL | NÃO APLICÁVEL |
|-------|----------|---------|---------------|-----------------|---------------|
{_status_table_row(_counts_row_label('RF', rf_n), rf_c)}
{_status_table_row(_counts_row_label('RNF', rnf_n), rnf_c)}
{_status_table_row(_counts_row_label('Decisões 4.2.3', len(d423)), dec_c)}
{_status_table_row(_counts_row_label('CE', ce_n), ce_c)}

## Itens parciais

{chr(10).join(parcial_itens) if parcial_itens else '- Nenhum.'}

## Falhas da regressão

{chr(10).join(f'- `{f}`' for f in falhas) if falhas else '- Nenhuma.'}
"""


def render_inventario(resultados: dict[str, Any], regressao: dict[str, Any]) -> str:
    aud = resultados.get("auditoria") or {}
    git = aud.get("git") or {}
    amb = aud.get("ambiente") or {}
    operacional = resultados.get("operacional_intact") or {}
    inv_before = regressao.get("inventory_before") or regressao.get("inventory") or {}
    return f"""# Inventário da auditoria

## Repositório

- Branch: `{git.get('branch') or '—'}`
- Commits: **{git.get('commits') if git.get('commits') is not None else 'não informado'}**
- HEAD: {git.get('head') or 'inexistente'}

## Versões

- Python venv: **{amb.get('python_venv') or '—'}**
- pytest: {amb.get('pytest') or '—'}
- Foundry/Forge: {amb.get('forge') or '—'}

## AGROTRACE_DATA_ROOT

- Isolamento: {amb.get('isolamento') or '—'}
- Inventário temp (regressão): `{json.dumps(inv_before, ensure_ascii=False)[:500]}`

## Bancos operacionais (hashes)

{render_db_status(operacional)}

## Divergência documental

{(resultados.get('divergencia_requirements_map_yaml') or {}).get('nota') or '—'}
"""


def render_comandos(resultados: dict[str, Any], regressao: dict[str, Any]) -> str:
    lines = [
        "# Comandos e resultados",
        "",
        f"Fonte: `_regressao.json` gerado em {regressao.get('generated_at_utc')}",
        "",
        f"**Pass:** {regressao.get('pass_count')} | **Fail:** {regressao.get('fail_count')} | "
        f"**Steps:** {len(regressao.get('results') or [])} | "
        f"**Duração total:** {sum(x.get('duration_ms') or 0 for x in (regressao.get('results') or []))} ms",
        "",
        "| # | Nome | Exit | Duração (ms) | Resumo |",
        "|---|------|------|--------------|--------|",
    ]
    for i, x in enumerate(regressao.get("results") or [], 1):
        summ = (x.get("summary") or "").replace("|", "/").replace("\n", " ")[:120]
        lines.append(
            f"| {i} | {x.get('name')} | {x.get('exit_code')} | {x.get('duration_ms')} | {summ} |"
        )
    lines += ["", "## Falhas", ""]
    for x in regressao.get("results") or []:
        if x.get("exit_code") not in (0, None):
            lines.append(f"### {x.get('name')}")
            lines.append(f"- comando: `{' '.join(x.get('command') or [])}`")
            lines.append(f"- cwd: `{x.get('cwd')}`")
            lines.append(f"- summary: {x.get('summary')}")
            err = (x.get("stderr_tail") or "").replace("\\", "/")
            lines.append(f"- stderr_tail:\n```\n{err}\n```")
            lines.append("")
    return "\n".join(lines)


def render_matriz(resultados: dict[str, Any]) -> str:
    rf_rows = [
        "| ID | Título | Status | Confiança | Teste | Lacunas |",
        "|----|--------|--------|-----------|-------|---------|",
    ]
    for r in resultados.get("RF") or []:
        rf_rows.append(
            f"| {r['id']} | {r['titulo']} | {r['status']} | {r['confianca']} | "
            f"{str(r.get('teste') or '')[:80]} | {r.get('lacunas') or '—'} |"
        )
    rnf_rows = [
        "| ID | Título | Status | Confiança | Teste | Lacunas |",
        "|----|--------|--------|-----------|-------|---------|",
    ]
    for r in resultados.get("RNF") or []:
        rnf_rows.append(
            f"| {r['id']} | {r['titulo']} | {r['status']} | {r['confianca']} | "
            f"{str(r.get('teste') or '')[:80]} | {r.get('lacunas') or '—'} |"
        )
    return f"""# Matriz de requisitos (PDF oficial)

## RF001–RF021

{chr(10).join(rf_rows)}

### Contagem RF
`{json.dumps(resultados.get('contagens', {}).get('RF') or count_by_status(resultados.get('RF') or []), ensure_ascii=False)}`

## RNF001–RNF012

{chr(10).join(rnf_rows)}

### Contagem RNF
`{json.dumps(resultados.get('contagens', {}).get('RNF') or count_by_status(resultados.get('RNF') or []), ensure_ascii=False)}`
"""


def render_decisoes(resultados: dict[str, Any]) -> str:
    d423, d4510 = split_decisions(resultados.get("decisoes") or [])
    lines_423 = [
        "| ID | Decisão | Status | Evidência |",
        "|----|---------|--------|-----------|",
    ]
    for d in d423:
        lines_423.append(
            f"| {d['id']} | {d['titulo']} | {d['status']} | {d.get('evidencia') or '—'} |"
        )
    lines_4510 = [
        "| ID | Decisão | Status | Evidência | Nota |",
        "|----|---------|--------|-----------|------|",
    ]
    for d in d4510:
        lines_4510.append(
            f"| {d['id']} | {d['titulo']} | {d['status']} | {d.get('evidencia') or '—'} | "
            f"{d.get('nota') or '—'} |"
        )
    cont = resultados.get("contagens") or {}
    return f"""# Decisões arquiteturais

## Cap. 4.2.3 (oficiais — {len(d423)})

{chr(10).join(lines_423)}

### Contagem 4.2.3
`{json.dumps(cont.get('decisoes_4_2_3') or count_by_status(d423), ensure_ascii=False)}`

## Seção 4.5.10 (complementar — {len(d4510)})

{chr(10).join(lines_4510)}

### Contagem complementar
`{json.dumps(cont.get('decisoes_complementares_4_5_10') or count_by_status(d4510), ensure_ascii=False)}`

Nota contagens: {(cont.get('decisoes') or {}).get('nota') or '—'}
"""


def render_cenarios(resultados: dict[str, Any]) -> str:
    ce_lines = [
        "| ID | Cenário | Status | Evidência |",
        "|----|---------|--------|-----------|",
    ]
    for c in resultados.get("CE") or []:
        ce_lines.append(
            f"| {c['id']} | {c['titulo']} | {c['status']} | {c.get('evidencia') or '—'} |"
        )
    return f"""# Cenários CE1–CE5

{chr(10).join(ce_lines)}

## Contagem
`{json.dumps(resultados.get('contagens', {}).get('CE') or count_by_status(resultados.get('CE') or []), ensure_ascii=False)}`
"""


def render_pendencias(resultados: dict[str, Any], regressao: dict[str, Any]) -> str:
    falhas = [
        x
        for x in (regressao.get("results") or [])
        if x.get("exit_code") not in (0, None)
    ]
    lines = ["# Pendências", ""]
    if not falhas:
        lines.append("Nenhuma falha na regressão.")
    for i, x in enumerate(falhas, 1):
        lines.append(f"## P{i} — `{x.get('name')}`")
        lines.append(f"- **Exit:** {x.get('exit_code')}")
        lines.append(f"- **Summary:** {x.get('summary')}")
        lines.append("")
    lacunas = []
    for r in (resultados.get("RF") or []) + (resultados.get("RNF") or []):
        if r.get("lacunas"):
            lacunas.append(f"- **{r['id']}:** {r['lacunas']}")
    if lacunas:
        lines.append("## Lacunas declaradas no JSON")
        lines.extend(lacunas)
    operacional = resultados.get("operacional_intact") or {}
    if operacional.get("provenance_match") is False:
        lines.append("")
        lines.append("## Integridade operacional")
        lines.append(f"- provenance.db alterado: {operacional.get('provenance_note') or 'sem nota'}")
    return "\n".join(lines)


def render_git_dados(resultados: dict[str, Any], regressao: dict[str, Any]) -> str:
    aud = resultados.get("auditoria") or {}
    git = aud.get("git") or {}
    operacional = resultados.get("operacional_intact") or {}
    intact_claim = _banks_summary(operacional)
    return f"""# Verificação Git e dados

## Git

- Branch: `{git.get('branch') or '—'}`
- Commits: {git.get('commits') if git.get('commits') is not None else 'não informado'}
- HEAD: {git.get('head') or 'inexistente'}

## Inventário operacional — hashes

{render_db_status(operacional)}

## Ambiente temporário

- {(aud.get('ambiente') or {}).get('isolamento') or '—'}
- Inventário regressão: before=`{bool(regressao.get('inventory_before'))}` after=`{bool(regressao.get('inventory_after'))}`

## Confirmação

{intact_claim}

Gerado em: {aud.get('generated_at_utc') or '—'}
"""


def render_all(resultados: dict[str, Any], regressao: dict[str, Any]) -> dict[str, str]:
    validate_counts(resultados)
    return {
        "00-resumo-executivo.md": render_resumo(resultados, regressao),
        "01-inventario.md": render_inventario(resultados, regressao),
        "02-comandos-e-resultados.md": render_comandos(resultados, regressao),
        "03-matriz-requisitos.md": render_matriz(resultados),
        "04-decisoes-arquiteturais.md": render_decisoes(resultados),
        "05-cenarios-ce1-ce5.md": render_cenarios(resultados),
        "07-pendencias.md": render_pendencias(resultados, regressao),
        "10-verificacao-git-e-dados.md": render_git_dados(resultados, regressao),
    }


def write_reports(out_dir: Path, reports: dict[str, str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in reports.items():
        (out_dir / name).write_text(text.strip() + "\n", encoding="utf-8")
        print("wrote", out_dir / name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera MD da auditoria a partir dos JSON")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_DIR,
        help="Diretório com 09-resultados.json e _regressao.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Diretório de saída (obrigatório — evita overwrite acidental)",
    )
    args = parser.parse_args(argv)
    res, reg = load_inputs(args.input_dir)
    reports = render_all(res, reg)
    write_reports(args.out, reports)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
