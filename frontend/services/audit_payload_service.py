"""Resolvedor de payloads técnicos para auditoria."""

from __future__ import annotations

import json
from typing import Any

from services.audit_event_service import most_recent_event
from utils.sanitize import sanitize_for_display


PAYLOAD_SOURCES = [
    ("cycle", "JSON do ciclo ativo"),
    ("event", "Evento selecionado / mais recente"),
    ("evidence", "Pacote de evidências"),
    ("anchoring", "Payload de ancoragem"),
    ("integrity", "Relatório de integridade"),
    ("raw_metadata", "Metadados do arquivo"),
    ("calculation", "Resultado de cálculo"),
    ("calculation_explanation", "Explicação do cálculo"),
    ("correction_history", "Histórico de correção"),
    ("normalized", "Dados normalizados (amostra)"),
    ("ontology", "Ontologia"),
    ("semantic", "Validação semântica"),
    ("version_manifest", "Mapa de versões (RNF010)"),
]


def _wrap(source: str, data: Any, title: str, **extra) -> dict[str, Any]:
    return {
        "source": source,
        "data": sanitize_for_display(data),
        "title": title,
        **extra,
    }


def resolve_payload(
    source: str,
    cycle: dict,
    *,
    selected_event: dict | None = None,
    events: list[dict] | None = None,
) -> dict[str, Any]:
    """Resolve payload JSON por origem selecionada (sanitizado)."""
    if not cycle.get("cycle_id"):
        return {"source": source, "data": None, "title": "Sem ciclo"}

    if source == "cycle":
        data = {k: v for k, v in cycle.items() if not str(k).startswith("_")}
        return _wrap(source, data, "JSON do ciclo ativo")

    if source == "event":
        evt = selected_event or most_recent_event(events or [])
        if not evt:
            return {"source": source, "data": None, "title": "Nenhum evento disponível"}
        payload = evt.get("payload_json") or evt.get("payload") or evt
        title = f"Evento: {evt.get('event_type', '—')} ({evt.get('created_at', '—')})"
        return _wrap(source, payload, title, event=sanitize_for_display(evt))

    if source == "evidence":
        return _wrap(source, cycle.get("evidence_package"), "Pacote de evidências")

    if source == "anchoring":
        return _wrap(source, cycle.get("anchoring"), "Payload de ancoragem")

    if source == "integrity":
        return _wrap(source, cycle.get("integrity"), "Relatório de integridade")

    if source == "raw_metadata":
        return _wrap(source, cycle.get("raw_file"), "Metadados do arquivo bruto")

    if source == "calculation":
        return _wrap(source, cycle.get("calculation"), "Resultado de cálculo preliminar")

    if source == "calculation_explanation":
        expl = (cycle.get("calculation") or {}).get("explanation")
        return _wrap(source, expl, "Explicação canônica do cálculo")

    if source == "correction_history":
        data = {
            "result_versions": cycle.get("result_versions") or [],
            "corrections": cycle.get("corrections") or [],
            "active_result_version_id": cycle.get("active_result_version_id"),
        }
        return _wrap(source, data, "Histórico de correção / versões")

    if source == "normalized":
        rows = cycle.get("normalized_data") or []
        data = rows[:20] if len(rows) > 20 else rows
        title = f"Dados normalizados ({len(rows)} registro(s), mostrando {len(data)})"
        return _wrap(source, data, title)

    if source == "ontology":
        return _wrap(source, cycle.get("ontology"), "Ontologia / modelo canônico")

    if source == "semantic":
        return _wrap(source, cycle.get("semantic_validation"), "Validação semântica")

    if source == "version_manifest":
        data = cycle.get("version_manifest")
        if not data:
            try:
                from services.version_manifest_service import build_version_manifest

                data = build_version_manifest(cycle).to_dict()
            except Exception:
                data = None
        return _wrap(source, data, "VersionManifest (RNF010)")

    return {"source": source, "data": None, "title": "Origem desconhecida"}


def payload_to_text(data: Any, *, max_chars: int = 12000) -> str:
    """Serializa payload para exibição."""
    if data is None:
        return "Nenhum dado disponível."
    try:
        text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(data)
    if len(text) > max_chars:
        return text[:max_chars] + "\n… (truncado)"
    return text
