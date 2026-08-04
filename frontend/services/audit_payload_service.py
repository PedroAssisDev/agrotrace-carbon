"""Resolvedor de payloads técnicos para auditoria."""

from __future__ import annotations

import json
from typing import Any

from services.audit_event_service import most_recent_event


PAYLOAD_SOURCES = [
    ("cycle", "JSON do ciclo ativo"),
    ("event", "Evento selecionado / mais recente"),
    ("evidence", "Pacote de evidências"),
    ("anchoring", "Payload de ancoragem"),
    ("integrity", "Relatório de integridade"),
    ("raw_metadata", "Metadados do arquivo"),
    ("calculation", "Resultado de cálculo"),
    ("normalized", "Dados normalizados (amostra)"),
    ("ontology", "Ontologia"),
    ("semantic", "Validação semântica"),
]


def resolve_payload(
    source: str,
    cycle: dict,
    *,
    selected_event: dict | None = None,
    events: list[dict] | None = None,
) -> dict[str, Any]:
    """Resolve payload JSON por origem selecionada."""
    if not cycle.get("cycle_id"):
        return {"source": source, "data": None, "title": "Sem ciclo"}

    if source == "cycle":
        data = {k: v for k, v in cycle.items() if not str(k).startswith("_")}
        return {"source": source, "data": data, "title": "JSON do ciclo ativo"}

    if source == "event":
        evt = selected_event or most_recent_event(events or [])
        if not evt:
            return {"source": source, "data": None, "title": "Nenhum evento disponível"}
        payload = evt.get("payload_json") or evt.get("payload") or evt
        title = f"Evento: {evt.get('event_type', '—')} ({evt.get('created_at', '—')})"
        return {"source": source, "data": payload, "title": title, "event": evt}

    if source == "evidence":
        data = cycle.get("evidence_package")
        return {"source": source, "data": data, "title": "Pacote de evidências"}

    if source == "anchoring":
        data = cycle.get("anchoring")
        return {"source": source, "data": data, "title": "Payload de ancoragem"}

    if source == "integrity":
        data = cycle.get("integrity")
        return {"source": source, "data": data, "title": "Relatório de integridade"}

    if source == "raw_metadata":
        data = cycle.get("raw_file")
        return {"source": source, "data": data, "title": "Metadados do arquivo bruto"}

    if source == "calculation":
        data = cycle.get("calculation")
        return {"source": source, "data": data, "title": "Resultado de cálculo preliminar"}

    if source == "normalized":
        rows = cycle.get("normalized_data") or []
        data = rows[:20] if len(rows) > 20 else rows
        title = f"Dados normalizados ({len(rows)} registro(s), mostrando {len(data)})"
        return {"source": source, "data": data, "title": title}

    if source == "ontology":
        data = cycle.get("ontology")
        return {"source": source, "data": data, "title": "Ontologia / modelo canônico"}

    if source == "semantic":
        data = cycle.get("semantic_validation")
        return {"source": source, "data": data, "title": "Validação semântica"}

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
