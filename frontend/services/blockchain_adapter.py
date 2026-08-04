"""Adapter para blockchain / pacote de evidências.

Correção principal desta refatoração: as etapas observe → build → anchor →
verify rodam em TRANSAÇÕES COMMITADAS SEPARADAS. A Unit of Work do
blockchain-service só faz auto-commit ao sair do ``with``; portanto, manter
observe e build no mesmo bloco fazia o ``build`` não encontrar o anchor request
recém-criado (caindo em mock). Agora cada etapa abre seu próprio
``with container.unit_of_work()`` e usa IDs reais entre blocos.

Cada função retorna ``mode``: ``"real"`` ou ``"mock"``. O fallback mock só é
usado quando ``config.ALLOW_MOCK_FALLBACK`` é ``True``; caso contrário o erro é
propagado para o chamador tratar.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import config
from services import direct_imports as di
from services.bootstrap import get_blockchain_container
from services.mock_data import mock_evidence_package, mock_integrity_check
from utils.date_helpers import now_iso
from utils.hash_helpers import official_package_hash  # noqa: F401 — kept for clarity; sha256_dict removed
from utils.pipeline_logging import ids_from_cycle, log_call, log_fail, timed_op, truncate

logger = logging.getLogger("agrotrace.blockchain")


class BlockchainUnavailable(RuntimeError):
    """Erro propagado quando a integração real falha e o mock não é permitido."""


def _autoflush_uow(container):
    """Cria uma Unit of Work com autoflush=True compartilhando o engine.

    O ``SimulateAnchoringUseCase`` faz ``add()`` seguido de ``update()`` no
    mesmo objeto; o ``update`` usa ``session.get`` que só enxerga a linha se a
    sessão tiver autoflush. A session factory padrão do serviço usa
    ``autoflush=False`` (não podemos alterar o serviço), então criamos uma UoW
    equivalente com autoflush ligado, ligada ao mesmo engine.
    """
    from sqlalchemy.orm import sessionmaker

    from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

    engine = container.session_factory.kw.get("bind")
    factory = sessionmaker(bind=engine, autoflush=True, autocommit=False, expire_on_commit=False)
    return SqlAlchemyUnitOfWork(factory)


def _available() -> bool:
    return (
        config.USE_DIRECT_FUNCTION_CALLS
        and not config.USE_MOCK_DATA
        and di.ObserveProvenanceEventsUseCase is not None
    )


def _handle_failure(exc: Exception, mock_builder, *, context: str):
    """Aplica a política de fallback mock conforme ALLOW_MOCK_FALLBACK."""
    log_fail(logger, "blockchain.failed", context=context, error=str(exc))
    if not config.ALLOW_MOCK_FALLBACK:
        raise BlockchainUnavailable(f"{context}: {exc}") from exc
    result = mock_builder()
    if isinstance(result, dict):
        result["fallback_reason"] = str(exc)
        log_call(logger, "blockchain.mock", mode="mock", context=context, reason=str(exc))
    return result


def _select_anchor_request_id(uow, observe, pipeline_run_id: str | None):
    """Escolhe o anchor request do ciclo atual (por pipeline_run_id)."""
    target = str(pipeline_run_id) if pipeline_run_id else None
    if target:
        for status in ("pending", "building", "failed"):
            try:
                for req in uow.anchor_requests.list_by_status(status):
                    if req.pipeline_run_id and str(req.pipeline_run_id) == target:
                        return req.anchor_request_id
            except Exception as exc:
                logger.warning(
                    "[CALL] blockchain.scan_anchor_requests status=%s error=%s",
                    status,
                    exc,
                )
                continue
    if observe and observe.created_request_ids:
        return observe.created_request_ids[0]
    return None


def create_evidence_package(cycle_data: dict) -> dict[str, Any]:
    """Observa eventos e constrói o pacote de evidências (transações separadas)."""
    ids = ids_from_cycle(cycle_data)
    if not _available():
        if config.ALLOW_MOCK_FALLBACK:
            pkg = mock_evidence_package(cycle_data)
            pkg["mode"] = "mock"
            _persist_package(pkg)
            log_call(logger, "evidence.mock", mode="mock", **ids, reason="service_unavailable")
            return pkg
        raise BlockchainUnavailable("blockchain-service indisponível (use cases não importados).")

    def _mock():
        pkg = mock_evidence_package(cycle_data)
        pkg["mode"] = "mock"
        _persist_package(pkg)
        return pkg

    log_call(logger, "evidence.start", **ids)
    with timed_op() as timer:
        try:
            container = get_blockchain_container()
            if container is None:
                raise RuntimeError("Blockchain container indisponível")

            pipeline_run_id = cycle_data.get("pipeline_run_id")

            # Reset do watermark do observer antes de observar.
            # Necessário porque o blockchain-service grava o watermark via
            # ``datetime.isoformat()`` (separador "T"), enquanto o created_at dos
            # eventos é gravado com separador " " (espaço). Como a comparação no
            # SQLite é textual e o espaço (0x20) é menor que "T" (0x54), eventos
            # novos ficariam "abaixo" do watermark e nunca seriam observados.
            # Resetar para a época (1970) faz o observe varrer todos os pendentes;
            # o próprio observe deduplica via get_by_source_event_id.
            epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
            with container.unit_of_work() as uow:
                try:
                    uow.observer_state.set_watermark(epoch)
                except Exception as exc:
                    logger.warning("[CALL] blockchain.reset_watermark error=%s", exc)

            # (a) OBSERVE — transação própria, commitada ao sair do with
            with container.unit_of_work() as uow:
                observe = di.ObserveProvenanceEventsUseCase(uow, container.event_reader).execute(
                    di.ObserveEventsCommand(limit=200)
                )

            # Seleciona o anchor request do ciclo atual em transação read-only
            with container.unit_of_work() as uow:
                anchor_request_id = _select_anchor_request_id(uow, observe, pipeline_run_id)

            if anchor_request_id is None:
                raise RuntimeError("Nenhum anchor request elegível encontrado após observe")

            # (b) BUILD — transação própria; o request já está commitado
            with container.unit_of_work() as uow:
                builder = di.BuildEvidencePackageUseCase(
                    uow, container.data_reader, container.event_reader
                )
                build = builder.execute(
                    di.BuildEvidencePackageCommand(anchor_request_id=anchor_request_id)
                )

            pkg = {
                "mode": "real",
                "evidence_package_id": str(build.evidence_package_id),
                "anchor_request_id": str(anchor_request_id),
                "pipeline_run_id": cycle_data.get("pipeline_run_id"),
                "property_id": cycle_data.get("property_id"),
                "property_name": cycle_data.get("property_name"),
                "reporting_period": cycle_data.get("reporting_period"),
                "ontology_version": (cycle_data.get("publication") or {}).get("ontology_version"),
                "calculation_execution_id": cycle_data.get("calculation_execution_id"),
                "methodology": (cycle_data.get("calculation") or {}).get("methodology", "IPCC/IDF-compatible"),
                "hashes": {
                    **(cycle_data.get("hashes") or {}),
                    "calculation_explanation": (
                        ((cycle_data.get("calculation") or {}).get("explanation") or {}).get("content_hash")
                    ),
                },
                "calculation_explanation_ref": {
                    "schema_version": ((cycle_data.get("calculation") or {}).get("explanation") or {}).get("schema_version"),
                    "content_hash": ((cycle_data.get("calculation") or {}).get("explanation") or {}).get("content_hash"),
                    "calculation_id": cycle_data.get("calculation_execution_id")
                    or ((cycle_data.get("calculation") or {}).get("explanation") or {}).get("calculation_id"),
                    "result_id": cycle_data.get("calculation_result_set_id")
                    or ((cycle_data.get("calculation") or {}).get("explanation") or {}).get("result_id"),
                },
                "package_hash": build.package_hash,
                "merkle_root": build.merkle_root,
                "created_at": now_iso(),
                "anchoring_status": "EVIDENCE_PACKAGE_CREATED",
            }
            _persist_package(pkg)
            log_call(
                logger,
                "evidence.done",
                mode="real",
                **ids,
                package_id=truncate(pkg["evidence_package_id"]),
                merkle_root=truncate(pkg.get("merkle_root")),
                duration_ms=timer.duration_ms,
            )
            return pkg
        except Exception as exc:
            return _handle_failure(exc, _mock, context="Pacote de evidências real")


def simulate_anchoring(evidence_package_id: str, network_code: str | None = None) -> dict[str, Any]:
    """Ancora o pacote na rede configurada (simulada ou EVM)."""
    network = network_code or getattr(config, "BLOCKCHAIN_DEFAULT_NETWORK_CODE", "local_simulated")
    if not _available():
        if config.ALLOW_MOCK_FALLBACK:
            log_call(
                logger,
                "anchor.mock",
                mode="mock",
                package_id=truncate(evidence_package_id),
                network=network,
                reason="service_unavailable",
            )
            return {
                "mode": "mock",
                "anchoring_status": "ANCHORING_SIMULATED",
                "transaction_id": "0xsim" + (evidence_package_id or "")[:8],
                "network": "local_simulated",
                "anchoring_kind": "SIMULADA",
            }
        raise BlockchainUnavailable("blockchain-service indisponível para ancoragem.")

    def _mock():
        return {
            "mode": "mock",
            "anchoring_status": "ANCHORING_SIMULATED",
            "transaction_id": "0xsim" + (evidence_package_id or "")[:8],
            "network": "local_simulated",
            "anchoring_kind": "SIMULADA",
        }

    log_call(logger, "anchor.start", package_id=truncate(evidence_package_id), network=network)
    with timed_op() as timer:
        try:
            if not evidence_package_id or evidence_package_id.startswith("EP-"):
                raise ValueError("ID de pacote mock — anchoring real não aplicável")

            container = get_blockchain_container()
            with _autoflush_uow(container) as uow:
                if di.AnchorEvidencePackageUseCase is not None and di.AnchorEvidencePackageCommand is not None:
                    result = di.AnchorEvidencePackageUseCase(uow, container.providers).execute(
                        di.AnchorEvidencePackageCommand(
                            evidence_package_id=UUID(evidence_package_id),
                            network_code=network,
                        )
                    )
                    is_simulated = result.anchoring_mode == "simulated" or network == "local_simulated"
                    out = {
                        "mode": "real",
                        "anchoring_status": result.anchoring_status,
                        "transaction_id": result.transaction_hash,
                        "block_number": result.block_number,
                        "network": result.network_code,
                        "chain_id": result.chain_id,
                        "contract_address": result.contract_address,
                        "evidence_key": result.evidence_key,
                        "package_hash": result.package_hash,
                        "merkle_root": result.merkle_root,
                        "gas_used": result.gas_used,
                        "explorer_url": result.explorer_url,
                        "idempotent_reuse": result.idempotent_reuse,
                        "anchoring_mode": result.anchoring_mode,
                        "anchoring_kind": "SIMULADA" if is_simulated else "CONFIRMADA EM REDE EVM",
                        "anchored_at": now_iso(),
                        "provider_response": result.provider_response,
                    }
                    log_call(
                        logger,
                        "anchor.done",
                        mode="real",
                        network=out["network"],
                        tx=truncate(out.get("transaction_id"), 14),
                        simulated=is_simulated,
                        duration_ms=timer.duration_ms,
                    )
                    return out

                # Compatibilidade: SimulateAnchoringUseCase
                result = di.SimulateAnchoringUseCase(uow, container.providers).execute(
                    di.SimulateAnchoringCommand(
                        evidence_package_id=UUID(evidence_package_id),
                        network_code=network,
                    )
                )
            out = {
                "mode": "real",
                "anchoring_status": result.anchoring_status,
                "transaction_id": result.transaction_hash,
                "block_number": result.block_number,
                "network": network,
                "anchoring_kind": "SIMULADA" if network == "local_simulated" else "CONFIRMADA EM REDE EVM",
                "anchored_at": now_iso(),
            }
            log_call(
                logger,
                "anchor.done",
                mode="real",
                network=network,
                tx=truncate(out.get("transaction_id"), 14),
                duration_ms=timer.duration_ms,
            )
            return out
        except Exception as exc:
            return _handle_failure(exc, _mock, context="Ancoragem")


def intentional_tamper_demo(package_hash: str, onchain_hash: str | None = None) -> dict[str, Any]:
    """In-memory adulteration demo — never mutates DB or original package.

    Uses the official blockchain-service canonicalization + SHA-256 when available.
    """
    original = {"package_hash": package_hash, "marker": "original"}
    tampered = {"package_hash": package_hash, "marker": "tampered-intentional"}
    if di.to_canonical_json and di.sha256_hex:
        original_hash = di.sha256_hex(original)
        tampered_hash = di.sha256_hex(tampered)
    else:
        raise RuntimeError(
            "blockchain-service sha256_hex unavailable for tamper demo "
            "(official json_canonical_v1 required)"
        )
    reference = onchain_hash or package_hash
    return {
        "intentional_test": True,
        "label": "TESTE DE ADULTERAÇÃO (cópia em memória — pacote original intacto)",
        "original": {
            "hash": original_hash,
            "matches_reference": original_hash.lower() == str(reference).lower()
            if str(reference).startswith("0x")
            else True,
        },
        "tampered": {
            "hash": tampered_hash,
            "matches_reference": tampered_hash.lower() == str(reference).lower()
            if reference and str(reference).startswith("0x")
            else False,
        },
        "integrity_original": "válida",
        "integrity_tampered": "inválida",
    }


def verify_integrity(evidence_package: dict, current_artifacts: dict | None = None) -> dict[str, Any]:
    """Verifica integridade do pacote real e monta a tabela por artefato."""
    tamper = bool((current_artifacts or {}).get("tamper", False))
    pkg_id = (evidence_package or {}).get("evidence_package_id")

    if not _available():
        if config.ALLOW_MOCK_FALLBACK:
            log_call(
                logger,
                "verify.mock",
                mode="mock",
                package_id=truncate(pkg_id),
                tamper=tamper,
                reason="service_unavailable",
            )
            return _mock_verification(tamper)
        raise BlockchainUnavailable("blockchain-service indisponível para verificação.")

    if not pkg_id or str(pkg_id).startswith("EP-"):
        if config.ALLOW_MOCK_FALLBACK:
            log_call(
                logger,
                "verify.mock",
                mode="mock",
                package_id=truncate(pkg_id),
                tamper=tamper,
                reason="invalid_package_id",
            )
            return _mock_verification(tamper)
        raise BlockchainUnavailable(f"evidence_package_id inválido para verificação real: {pkg_id!r}")

    log_call(logger, "verify.start", package_id=truncate(pkg_id), tamper=tamper)
    with timed_op() as timer:
        try:
            container = get_blockchain_container()
            with container.unit_of_work() as uow:
                result = di.VerifyEvidencePackageUseCase(uow).execute(
                    di.VerifyEvidencePackageCommand(evidence_package_id=UUID(str(pkg_id)))
                )

            details = result.details or {}
            is_valid = bool(result.is_valid) and not tamper

            rows: list[dict] = []
            # details["items"] é uma lista de {item_id, expected, computed, is_valid}
            for item in details.get("items", []) or []:
                anchored = item.get("expected", "—")
                current = item.get("computed", "—")
                item_valid = bool(item.get("is_valid"))
                if tamper:
                    # Simula adulteração do primeiro artefato para o caso divergente
                    current = (current or "")[:-4] + "dead" if current else "tampered"
                    item_valid = False
                rows.append({
                    "artifact": _short_item_label(item.get("item_id", "item")),
                    "anchored_hash": anchored,
                    "recalculated_hash": current,
                    "status": "íntegro" if item_valid else "divergente",
                })

            rows.append({
                "artifact": "Package Hash",
                "anchored_hash": evidence_package.get("package_hash", "—"),
                "recalculated_hash": evidence_package.get("package_hash", "—") if not tamper else "—",
                "status": "íntegro" if details.get("package_hash_valid") and not tamper else "divergente",
            })
            rows.append({
                "artifact": "Merkle Root",
                "anchored_hash": evidence_package.get("merkle_root", "—"),
                "recalculated_hash": evidence_package.get("merkle_root", "—") if not tamper else "—",
                "status": "íntegro" if details.get("merkle_root_valid") and not tamper else "divergente",
            })

            out = {
                "mode": "real",
                "is_valid": is_valid,
                "final_status": "VERIFICADO / ÍNTEGRO" if is_valid else "FALHA DE INTEGRIDADE / POSSÍVEL ALTERAÇÃO",
                "message": (
                    "Todos os hashes recalculados conferem com os ancorados. O pacote é íntegro."
                    if is_valid
                    else "Um ou mais hashes recalculados divergem dos ancorados. Possível alteração nos dados."
                ),
                "rows": rows,
                "details": details,
                "tamper_simulated": tamper,
            }
            log_call(
                logger,
                "verify.done",
                mode="real",
                package_id=truncate(pkg_id),
                is_valid=is_valid,
                duration_ms=timer.duration_ms,
            )
            return out
        except Exception as exc:
            return _handle_failure(exc, lambda: _mock_verification(tamper), context="Verificação real")


def compute_local_hashes(cycle: dict) -> dict[str, str]:
    """Calcula hashes locais dos artefatos do ciclo (prioriza manifesto publicado)."""
    if di.sha256_hex is None:
        raise RuntimeError(
            "blockchain-service sha256_hex unavailable for local hashes "
            "(official json_canonical_v1 required; no compact-JSON fallback)"
        )
    hasher = di.sha256_hex
    pub = cycle.get("publication") or {}
    try:
        from services.publication_service import evidence_input_from_publication

        evidence_in = evidence_input_from_publication(cycle) if pub else {}
        return {
            "raw_file_hash": pub.get("original_file_hash") or (cycle.get("raw_file") or {}).get("sha256") or hasher({"raw": "empty"}),
            "normalized_batch_hash": pub.get("normalized_hash") or hasher({"normalized": len(cycle.get("normalized_data", []))}),
            "canonical_dataset_hash": pub.get("ontology_hash") or hasher(cycle.get("ontology") or {}),
            "semantic_validation_hash": hasher(cycle.get("semantic_validation") or {}),
            "preliminary_result_hash": (cycle.get("calculation") or {}).get("preliminary_hash") or hasher({"calc": 0}),
            "approval_record_hash": hasher(cycle.get("approval") or {}),
            "final_ontology_hash": pub.get("ontology_hash") or hasher({"ont": 0}),
            "publication_hash": pub.get("publication_hash") or hasher(evidence_in or {"pub": 0}),
        }
    except RuntimeError:
        raise
    except Exception:
        return {
            "raw_file_hash": (cycle.get("raw_file") or {}).get("sha256") or hasher({"raw": "empty"}),
            "normalized_batch_hash": hasher({"normalized": len(cycle.get("normalized_data", []))}),
            "canonical_dataset_hash": hasher(cycle.get("ontology") or {}),
            "semantic_validation_hash": hasher(cycle.get("semantic_validation") or {}),
            "preliminary_result_hash": (cycle.get("calculation") or {}).get("preliminary_hash") or "",
            "approval_record_hash": hasher(cycle.get("approval") or {}),
            "final_ontology_hash": (cycle.get("publication") or {}).get("ontology_hash") or "",
            "publication_hash": (cycle.get("publication") or {}).get("publication_hash") or "",
        }


def _mock_verification(tamper: bool) -> dict[str, Any]:
    out = mock_integrity_check(integrate=not tamper)
    out["mode"] = "mock"
    out["tamper_simulated"] = tamper
    return out


def _short_item_label(item_id: str) -> str:
    return f"Evidence item {str(item_id)[:8]}"


def _persist_package(pkg: dict) -> None:
    config.EVIDENCE_PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    eid = pkg.get("evidence_package_id", "unknown")
    path = config.EVIDENCE_PACKAGES_DIR / f"{eid}.json"
    path.write_text(json.dumps(pkg, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def build_package_summary_rows(cycles: list[dict]) -> list[dict]:
    """Linhas de resumo de pacotes de evidência por ciclo."""
    return [{
        "ciclo": c.get("cycle_id"),
        "propriedade": c.get("property_name"),
        "período": c.get("reporting_period"),
        "pacote": (c.get("evidence_package") or {}).get("evidence_package_id", "—"),
        "status": (c.get("steps") or {}).get("blockchain", {}).get("status", "—"),
    } for c in cycles if (c.get("evidence_package") or {}).get("evidence_package_id")]


def build_verify_cycle_options(cycles: list[dict]) -> list[dict]:
    """Opções de dropdown para verificação de integridade."""
    options = []
    for c in cycles:
        pkg = c.get("evidence_package") or {}
        if pkg.get("evidence_package_id"):
            options.append({
                "label": f"{c.get('cycle_id')} — {c.get('reporting_period')} — {pkg.get('evidence_package_id', '')[:12]}…",
                "value": c.get("cycle_id"),
            })
    return options


def integrity_status_message(integrity: dict) -> str:
    """Mensagem amigável do status de verificação."""
    if integrity.get("message"):
        return integrity["message"]
    if integrity.get("is_valid"):
        return "Todos os hashes recalculados conferem com os ancorados."
    return "Execute a verificação para comparar hashes."
