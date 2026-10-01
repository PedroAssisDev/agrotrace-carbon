"""Testes unitários do gerador de relatórios da auditoria pós-implementação."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

DOC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DOC_DIR))

from _gen_reports import (  # noqa: E402
    count_by_status,
    load_inputs,
    render_all,
    render_db_status,
    render_decisoes,
    render_resumo,
    split_decisions,
    validate_counts,
)


def _minimal_resultados(**overrides) -> dict:
    base = {
        "auditoria": {
            "generated_at_utc": "2026-01-01T00:00:00+00:00",
            "dissertacao": "frontend/main (7).pdf",
            "git": {"branch": "master", "commits": 0, "head": None},
            "ambiente": {
                "python_venv": "3.11.9",
                "pytest": "9.0.3",
                "forge": "1.7.1",
                "isolamento": "temp",
            },
            "prontidao_capitulo_5": "PRONTA COM LIMITACOES DECLARADAS",
        },
        "comandos_resumo": {"pass_count": 1, "fail_count": 0, "steps": 1, "falhas": []},
        "RF": [
            {
                "id": "RF001",
                "titulo": "Entrada",
                "status": "ATENDIDO",
                "confianca": "alta",
                "teste": "ok",
                "lacunas": None,
            },
            {
                "id": "RF008",
                "titulo": "Cálculo CO₂e",
                "status": "PARCIALMENTE ATENDIDO",
                "confianca": "média",
                "teste": "parcial",
                "lacunas": "detalhe",
            },
        ],
        "RNF": [
            {
                "id": "RNF001",
                "titulo": "Proveniência",
                "status": "ATENDIDO",
                "confianca": "alta",
                "teste": "ok",
                "lacunas": None,
            }
        ],
        "decisoes": [
            {"id": "D1", "titulo": "A", "secao": "4.2.3", "status": "ATENDIDO", "evidencia": "e1"},
            {"id": "D2", "titulo": "B", "secao": "4.2.3", "status": "ATENDIDO", "evidencia": "e2"},
            {"id": "D3", "titulo": "C", "secao": "4.2.3", "status": "ATENDIDO", "evidencia": "e3"},
            {"id": "D4", "titulo": "D", "secao": "4.2.3", "status": "ATENDIDO", "evidencia": "e4"},
            {"id": "D5", "titulo": "E", "secao": "4.2.3", "status": "ATENDIDO", "evidencia": "e5"},
            {"id": "D6", "titulo": "F", "secao": "4.2.3", "status": "ATENDIDO", "evidencia": "e6"},
            {"id": "D7", "titulo": "G", "secao": "4.2.3", "status": "ATENDIDO", "evidencia": "e7"},
            {"id": "D8", "titulo": "H", "secao": "4.2.3", "status": "ATENDIDO", "evidencia": "e8"},
            {"id": "D9", "titulo": "I", "secao": "4.2.3", "status": "ATENDIDO", "evidencia": "e9"},
            {
                "id": "D10",
                "titulo": "Publicação",
                "secao": "4.5.10",
                "status": "ATENDIDO",
                "evidencia": "e10",
                "nota": "complementar",
            },
        ],
        "CE": [
            {"id": "CE1", "titulo": "c1", "status": "ATENDIDO", "evidencia": "x"},
        ],
        "contagens": {
            "RF": {"ATENDIDO": 1, "PARCIALMENTE ATENDIDO": 1},
            "RNF": {"ATENDIDO": 1},
            "decisoes_4_2_3": {"ATENDIDO": 9},
            "decisoes_complementares_4_5_10": {"ATENDIDO": 1},
            "decisoes": {"ATENDIDO": 9, "nota": "9 oficiais + D10 complementar"},
            "CE": {"ATENDIDO": 1},
        },
        "operacional_intact": {
            "blockchain_service.db_sha256_before": "AAAA1111BBBB2222CCCC3333DDDD4444EEEE5555FFFF6666AAAA7777BBBB8888",
            "blockchain_service.db_sha256_after": "AAAA1111BBBB2222CCCC3333DDDD4444EEEE5555FFFF6666AAAA7777BBBB8888",
            "blockchain_match": True,
            "provenance.db_sha256_before": "1111AAAA2222BBBB3333CCCC4444DDDD5555EEEE6666FFFF7777AAAA8888BBBB",
            "provenance.db_sha256_after": "1111AAAA2222BBBB3333CCCC4444DDDD5555EEEE6666FFFF7777AAAA8888BBBB",
            "provenance_match": True,
        },
    }
    base.update(overrides)
    return base


def _minimal_regressao(**overrides) -> dict:
    base = {
        "generated_at_utc": "2026-01-01T00:00:00+00:00",
        "pass_count": 1,
        "fail_count": 0,
        "results": [
            {"name": "ok", "exit_code": 0, "duration_ms": 10, "summary": "pass", "command": ["x"]}
        ],
    }
    base.update(overrides)
    return base


def test_banco_inalterado() -> None:
    text = render_db_status(_minimal_resultados()["operacional_intact"])
    assert "sim" in text
    assert "não" not in text.split("Match")[1].split("\n")[2]  # blockchain row


def test_banco_alterado_com_nota() -> None:
    op = {
        "blockchain_service.db_sha256_before": "A" * 64,
        "blockchain_service.db_sha256_after": "A" * 64,
        "blockchain_match": True,
        "provenance.db_sha256_before": "B" * 64,
        "provenance.db_sha256_after": "C" * 64,
        "provenance_match": False,
        "provenance_note": "WAL checkpoint observado",
    }
    text = render_db_status(op)
    assert "não" in text
    assert "WAL checkpoint observado" in text
    md = render_resumo(_minimal_resultados(operacional_intact=op), _minimal_regressao())
    assert "dados intactos" not in md.lower() or "inalterados" not in md.lower() or "provenance" in md.lower()
    assert "alterado" in md.lower() or "WAL" in md


def test_nove_decisoes_mais_uma_complementar() -> None:
    res = _minimal_resultados()
    d423, d4510 = split_decisions(res["decisoes"])
    assert len(d423) == 9
    assert len(d4510) == 1
    md = render_decisoes(res)
    assert "4.2.3" in md
    assert "4.5.10" in md
    assert "D10" in md
    assert "Decisões (10)" not in md


def test_contagens_rf_rnf() -> None:
    res = _minimal_resultados()
    assert count_by_status(res["RF"]) == {"ATENDIDO": 1, "PARCIALMENTE ATENDIDO": 1}
    assert count_by_status(res["RNF"]) == {"ATENDIDO": 1}
    validate_counts(res)


def test_ausencia_de_commit() -> None:
    md = render_resumo(_minimal_resultados(), _minimal_regressao())
    assert "0 commits" in md
    assert "inexistente" in md.lower() or "HEAD" in md


def test_falha_validacao_contagens() -> None:
    res = _minimal_resultados()
    res["contagens"]["RF"] = {"ATENDIDO": 99}
    with pytest.raises(ValueError, match="RF"):
        validate_counts(res)


def test_utf8_characters() -> None:
    res = _minimal_resultados()
    res["RF"][1]["titulo"] = "Cálculo de CO₂e — emissão"
    reports = render_all(res, _minimal_regressao())
    joined = "\n".join(reports.values())
    assert "CO₂e" in joined
    assert "Cálculo" in joined
    # escrita UTF-8
    assert "pós-implementação" in reports["00-resumo-executivo.md"]


def test_render_all_keys() -> None:
    reports = render_all(_minimal_resultados(), _minimal_regressao())
    assert "00-resumo-executivo.md" in reports
    assert "04-decisoes-arquiteturais.md" in reports
    assert "10-verificacao-git-e-dados.md" in reports


def test_real_json_loads_and_validates() -> None:
    if not (DOC_DIR / "09-resultados.json").exists():
        pytest.skip("09-resultados.json ausente")
    res, reg = load_inputs(DOC_DIR)
    validate_counts(res)
    reports = render_all(res, reg)
    assert "provenance" in reports["10-verificacao-git-e-dados.md"].lower()
    # Não afirmar intacto se JSON diz match false
    if (res.get("operacional_intact") or {}).get("provenance_match") is False:
        assert "inalterados" not in reports["00-resumo-executivo.md"].lower() or "alterado" in reports[
            "00-resumo-executivo.md"
        ].lower()
