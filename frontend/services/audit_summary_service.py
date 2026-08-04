"""Resumo da auditoria técnica — cards, banners e modo de dados."""

from __future__ import annotations

from typing import Any

from services.audit_compliance_service import compliance_summary
from services.blockchain_view_service import blockchain_lock_message, is_blockchain_unlocked
from services.cycle_status_service import resolve_managerial_status
from services.integrity_view_service import integrity_message
from services.page_context import PageContext
from utils.global_filter import period_in_analysis_range


def detect_integration_mode(cycle: dict) -> str:
    """Detecta modo real / mock / mixed varrendo steps e artefatos."""
    modes: set[str] = set()
    if cycle.get("demo_mode"):
        modes.add("mock")

    for step in (cycle.get("steps") or {}).values():
        m = step.get("mode") or step.get("source")
        if m in {"real", "mock"}:
            modes.add(m)
        elif m:
            modes.add("mock" if "mock" in str(m).lower() else "real")

    for key in ("evidence_package", "anchoring", "integrity", "wrapper", "calculation"):
        block = cycle.get(key) or {}
        m = block.get("mode") or block.get("source")
        if m in {"real", "mock"}:
            modes.add(m)
        if block.get("fallback_reason"):
            modes.add("mock")

    if not modes:
        return "real"
    if modes == {"mock"}:
        return "mock"
    if "real" in modes and "mock" in modes:
        return "mixed"
    return modes.pop()


def build_consistency_banners(ctx: PageContext) -> list[dict[str, str]]:
    """Banners de inconsistência entre ciclo ativo e filtro global."""
    banners: list[dict[str, str]] = []
    active = ctx.active_cycle
    if not active.get("cycle_id"):
        return banners

    cycle_id = active.get("cycle_id")
    in_analysis = any(c.get("cycle_id") == cycle_id for c in ctx.analysis_cycles)
    in_filtered = any(c.get("cycle_id") == cycle_id for c in ctx.filtered_analysis_cycles)

    if ctx.analysis_cycles and not in_analysis:
        banners.append({
            "variant": "warning",
            "title": "Ciclo fora do período analítico",
            "message": (
                "O ciclo selecionado não pertence ao período analítico filtrado. "
                "Selecione um ciclo dentro do filtro ou ajuste o período na navbar."
            ),
        })

    if ctx.data_mode == "official_only" and ctx.no_official_data:
        banners.append({
            "variant": "info",
            "title": "Ciclos preliminares ocultos",
            "message": (
                "O filtro atual exibe apenas dados oficiais. "
                "Existem ciclos preliminares ocultos neste período."
            ),
        })
    elif ctx.data_mode == "official_only" and in_analysis and not in_filtered:
        banners.append({
            "variant": "info",
            "title": "Ciclo preliminar ativo",
            "message": (
                "O ciclo selecionado é preliminar e está oculto do escopo analítico oficial. "
                "Altere o modo de dados na navbar para incluir preliminares."
            ),
        })

    gf = ctx.global_filter or {}
    period = active.get("reporting_period")
    if period and gf.get("analysis_period_start") and not period_in_analysis_range(
        period, gf.get("analysis_period_start"), gf.get("analysis_period_end")
    ):
        banners.append({
            "variant": "warning",
            "title": "Período do ciclo diverge do filtro",
            "message": (
                f"O ciclo {cycle_id} ({period}) está fora da janela "
                f"{gf.get('period_display_label', 'analítica')}."
            ),
        })

    return banners


def _card(
    key: str,
    title: str,
    status: str,
    description: str,
    service: str,
    action: str | None = None,
    action_href: str | None = None,
    variant: str = "secondary",
) -> dict[str, Any]:
    return {
        "key": key,
        "title": title,
        "status": status,
        "description": description,
        "service": service,
        "action": action,
        "action_href": action_href,
        "variant": variant,
    }


def build_summary_cards(ctx: PageContext) -> list[dict[str, Any]]:
    """Cards principais do resumo da auditoria."""
    cycle = ctx.active_cycle
    if not cycle.get("cycle_id"):
        return []

    mgr = resolve_managerial_status(cycle)
    compliance = compliance_summary(cycle)
    unlocked = is_blockchain_unlocked(cycle)
    integration_mode = detect_integration_mode(cycle)
    integrity = cycle.get("integrity") or {}
    raw = cycle.get("raw_file") or {}
    prov_count = len(cycle.get("provenance_events") or [])

    mode_label = {"real": "Dados reais", "mock": "Dados simulados", "mixed": "Dados mistos"}.get(
        integration_mode, "—"
    )

    cards = [
        _card(
            "cycle",
            "Ciclo auditado",
            mgr.label,
            f"{cycle.get('cycle_id')} • {cycle.get('property_name', '—')} • {cycle.get('reporting_period', '—')}",
            "Frontend",
            variant=mgr.variant,
        ),
        _card(
            "audit_status",
            "Status geral da auditoria",
            compliance["overall"],
            f"{compliance['counts'].get('OK', 0)} OK • {compliance['counts'].get('Pendente', 0)} pendentes • {compliance['counts'].get('Erro', 0)} erros",
            "audit_compliance_service",
        ),
        _card(
            "cycle_status",
            "Status do ciclo",
            cycle.get("current_status", "—").replace("_", " ").title(),
            f"Progresso: {compliance['counts'].get('OK', 0)}/{len(compliance['matrix'])} itens conformes",
            "cycle_state",
        ),
        _card(
            "raw_file",
            "Arquivo bruto",
            "Completo" if raw.get("sha256") else "Pendente",
            raw.get("original_filename") or "Nenhum arquivo registrado",
            "Frontend / save-file",
            action="Ir para Entrada de Dados" if not raw else None,
            action_href="/data-entry" if not raw else None,
        ),
        _card(
            "provenance",
            "Proveniência",
            f"{prov_count} evento(s)" if prov_count else "Pendente",
            "Linha de eventos registrada pelo traceability-service",
            "traceability-service",
            action="Ver proveniência",
            action_href="#ta-provenance",
        ),
        _card(
            "publication",
            "Publicação final",
            "Concluída" if unlocked else "Pendente",
            "Versão final da ontologia aprovada e publicada" if unlocked else "Aguardando aprovação e publicação",
            "ontology-manager",
            action="Ir para Aprovação" if not unlocked else None,
            action_href="/approval" if not unlocked else None,
        ),
        _card(
            "blockchain",
            "Blockchain",
            "Liberado" if unlocked else "Bloqueado",
            blockchain_lock_message(cycle) or ("Evidências disponíveis para auditoria" if unlocked else "Gate ativo"),
            "blockchain-service",
            variant="success" if unlocked else "warning",
        ),
        _card(
            "integrity",
            "Integridade",
            "Íntegro" if integrity.get("is_valid") else (
                "Divergente" if integrity.get("is_valid") is False else "Não verificado"
            ),
            integrity_message(integrity),
            "blockchain-service",
            variant="success" if integrity.get("is_valid") else (
                "danger" if integrity.get("is_valid") is False else "secondary"
            ),
        ),
        _card(
            "data_mode",
            "Dados reais/simulados",
            mode_label,
            "Modo de integração detectado nos artefatos e etapas",
            "adapters",
            variant="dados-reais" if integration_mode == "real" else "fallback-mock",
        ),
        _card(
            "alerts",
            "Alertas e erros",
            f"{len(cycle.get('errors') or [])} erro(s), {len(cycle.get('warnings') or [])} alerta(s)",
            "Erros críticos e alertas do ciclo",
            "Frontend",
            variant="danger" if cycle.get("errors") else ("warning" if cycle.get("warnings") else "secondary"),
        ),
    ]
    return cards


def build_main_message(cycle: dict) -> dict[str, str]:
    """Mensagem principal do resumo."""
    unlocked = is_blockchain_unlocked(cycle)
    if unlocked:
        return {
            "variant": "success",
            "title": "Ciclo com versão final publicada",
            "message": (
                "Este ciclo possui versão final publicada. "
                "Evidências, Merkle Root e verificação de integridade podem ser auditadas."
            ),
        }
    return {
        "variant": "info",
        "title": "Ciclo sem versão final publicada",
        "message": (
            "Este ciclo ainda não possui versão final publicada. "
            "A proveniência pode ser auditada, mas o blockchain permanece bloqueado."
        ),
    }


def build_audit_summary(ctx: PageContext) -> dict[str, Any]:
    """Pacote completo do resumo."""
    cycle = ctx.active_cycle
    return {
        "cards": build_summary_cards(ctx),
        "main_message": build_main_message(cycle) if cycle.get("cycle_id") else None,
        "compliance": compliance_summary(cycle) if cycle.get("cycle_id") else None,
        "banners": build_consistency_banners(ctx),
        "integration_mode": detect_integration_mode(cycle) if cycle.get("cycle_id") else None,
    }
