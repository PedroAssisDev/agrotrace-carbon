"""Regressão do scanner de segredos — padrões contextuais (RNF012)."""

from __future__ import annotations

from pathlib import Path

from scripts.scan_secrets import _is_contextual_private_key, scan_tree


def test_hash_field_not_flagged(tmp_path: Path) -> None:
    f = tmp_path / "cycle.json"
    f.write_text(
        '{"package_hash": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
        ' "merkle_root": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}',
        encoding="utf-8",
    )
    findings = scan_tree(tmp_path)
    assert not any(x["type"] == "private_key_hex" for x in findings)


def test_private_key_assignment_flagged(tmp_path: Path) -> None:
    f = tmp_path / "leak.env.example.bak"
    # use .txt so scanner picks it up
    f = tmp_path / "config.txt"
    f.write_text(
        "BLOCKCHAIN_PRIVATE_KEY=0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
        encoding="utf-8",
    )
    findings = scan_tree(tmp_path)
    types = {x["type"] for x in findings}
    assert "private_key_env_assignment" in types or "private_key_hex" in types


def test_contextual_helper() -> None:
    assert not _is_contextual_private_key(
        'package_hash: "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"'
    )
    assert _is_contextual_private_key(
        'private_key = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"'
    )
