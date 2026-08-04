from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass

from app.application.container import ServiceContainer, init_database
from app.application.dto.commands import (
    AnchorEvidencePackageCommand,
    BuildEvidencePackageCommand,
    GenerateAuditReportCommand,
    ObserveEventsCommand,
    QueryAnchoredEvidenceCommand,
    ReprocessFailedAnchoringCommand,
    SimulateAnchoringCommand,
    VerifyAnchoredEvidenceCommand,
    VerifyEvidencePackageCommand,
)
from app.application.use_cases.anchor_evidence_package import AnchorEvidencePackageUseCase
from app.application.use_cases.build_evidence_package import BuildEvidencePackageUseCase
from app.application.use_cases.generate_audit_report import GenerateAuditReportUseCase
from app.application.use_cases.observe_provenance_events import ObserveProvenanceEventsUseCase
from app.application.use_cases.process_anchor_requests import ProcessAnchorRequestsUseCase
from app.application.use_cases.query_anchored_evidence import QueryAnchoredEvidenceUseCase
from app.application.use_cases.reprocess_failed_anchoring import ReprocessFailedAnchoringUseCase
from app.application.use_cases.simulate_anchoring import SimulateAnchoringUseCase
from app.application.use_cases.verify_anchored_evidence import VerifyAnchoredEvidenceUseCase
from app.application.use_cases.verify_evidence_package import VerifyEvidencePackageUseCase
from app.shared.ids import ensure_uuid


def _print_json(data: object) -> None:
    if is_dataclass(data) and not isinstance(data, type):
        data = asdict(data)
    print(json.dumps(data, indent=2, default=str))


def _anchor_payload(result) -> dict:
    return {
        "evidence_package_id": str(result.evidence_package_id),
        "network_code": result.network_code,
        "chain_id": result.chain_id,
        "contract_address": result.contract_address,
        "evidence_key": result.evidence_key,
        "package_hash": result.package_hash,
        "merkle_root": result.merkle_root,
        "transaction_hash": result.transaction_hash,
        "block_number": result.block_number,
        "anchoring_status": result.anchoring_status,
        "receipt_status": result.receipt_status,
        "gas_used": result.gas_used,
        "effective_gas_price": result.effective_gas_price,
        "explorer_url": result.explorer_url,
        "idempotent_reuse": result.idempotent_reuse,
        "anchoring_mode": result.anchoring_mode,
    }


def cmd_observe_events(args: argparse.Namespace) -> int:
    container = ServiceContainer()
    init_database(container.settings)
    with container.unit_of_work() as uow:
        result = ObserveProvenanceEventsUseCase(uow, container.event_reader).execute(
            ObserveEventsCommand(limit=args.limit)
        )
        _print_json(
            {
                "created_request_ids": [str(item) for item in result.created_request_ids],
                "skipped_event_ids": result.skipped_event_ids,
            }
        )
    return 0


def cmd_process_anchor_requests(args: argparse.Namespace) -> int:
    container = ServiceContainer()
    init_database(container.settings)
    with container.unit_of_work() as uow:
        package_ids = ProcessAnchorRequestsUseCase(uow, container.data_reader).execute(limit=args.limit)
        _print_json({"package_ids": package_ids})
    return 0


def cmd_build_evidence_package(args: argparse.Namespace) -> int:
    container = ServiceContainer()
    init_database(container.settings)
    with container.unit_of_work() as uow:
        command = BuildEvidencePackageCommand(
            anchor_request_id=ensure_uuid(args.anchor_request_id) if args.anchor_request_id else None,
            source_event_id=args.event_id,
        )
        result = BuildEvidencePackageUseCase(uow, container.data_reader).execute(command)
        _print_json(
            {
                "evidence_package_id": str(result.evidence_package_id),
                "package_hash": result.package_hash,
                "merkle_root": result.merkle_root,
            }
        )
    return 0


def cmd_simulate_anchoring(args: argparse.Namespace) -> int:
    container = ServiceContainer()
    init_database(container.settings)
    with container.unit_of_work() as uow:
        result = SimulateAnchoringUseCase(uow, container.providers).execute(
            SimulateAnchoringCommand(
                evidence_package_id=ensure_uuid(args.package_id),
                network_code=args.network_code,
            )
        )
        _print_json(
            {
                "evidence_package_id": str(result.evidence_package_id),
                "transaction_hash": result.transaction_hash,
                "block_number": result.block_number,
                "anchoring_status": result.anchoring_status,
            }
        )
    return 0


def cmd_anchor_package(args: argparse.Namespace) -> int:
    container = ServiceContainer()
    init_database(container.settings)
    with container.unit_of_work() as uow:
        result = AnchorEvidencePackageUseCase(uow, container.providers).execute(
            AnchorEvidencePackageCommand(
                evidence_package_id=ensure_uuid(args.package_id),
                network_code=args.network_code,
            )
        )
        _print_json(_anchor_payload(result))
    return 0


def cmd_query_anchor(args: argparse.Namespace) -> int:
    container = ServiceContainer()
    init_database(container.settings)
    with container.unit_of_work() as uow:
        result = QueryAnchoredEvidenceUseCase(uow, container.providers).execute(
            QueryAnchoredEvidenceCommand(
                evidence_package_id=ensure_uuid(args.package_id),
                network_code=args.network_code,
            )
        )
        _print_json(result)
    return 0


def cmd_verify_anchor(args: argparse.Namespace) -> int:
    container = ServiceContainer()
    init_database(container.settings)
    with container.unit_of_work() as uow:
        result = VerifyAnchoredEvidenceUseCase(uow, container.providers).execute(
            VerifyAnchoredEvidenceCommand(
                evidence_package_id=ensure_uuid(args.package_id),
                network_code=args.network_code,
            )
        )
        _print_json(
            {
                "evidence_package_id": str(result.evidence_package_id),
                "offchain_valid": result.offchain_valid,
                "onchain_found": result.onchain_found,
                "package_hash_match": result.package_hash_match,
                "merkle_root_match": result.merkle_root_match,
                "network_match": result.network_match,
                "contract_match": result.contract_match,
                "overall_valid": result.overall_valid,
                "details": result.details,
            }
        )
    return 0


def cmd_verify_package(args: argparse.Namespace) -> int:
    container = ServiceContainer()
    init_database(container.settings)
    with container.unit_of_work() as uow:
        result = VerifyEvidencePackageUseCase(uow).execute(
            VerifyEvidencePackageCommand(evidence_package_id=ensure_uuid(args.package_id))
        )
        _print_json(
            {
                "evidence_package_id": str(result.evidence_package_id),
                "is_valid": result.is_valid,
                "details": result.details,
            }
        )
    return 0


def cmd_reprocess_failed(args: argparse.Namespace) -> int:
    container = ServiceContainer()
    init_database(container.settings)
    with container.unit_of_work() as uow:
        processed = ReprocessFailedAnchoringUseCase(
            uow, container.data_reader, container.providers
        ).execute(ReprocessFailedAnchoringCommand(limit=args.limit))
        _print_json({"processed_request_ids": processed})
    return 0


def cmd_audit_report(args: argparse.Namespace) -> int:
    container = ServiceContainer()
    init_database(container.settings)
    with container.unit_of_work() as uow:
        result = GenerateAuditReportUseCase(uow).execute(
            GenerateAuditReportCommand(
                anchor_request_id=ensure_uuid(args.anchor_request_id)
                if args.anchor_request_id
                else None,
                evidence_package_id=ensure_uuid(args.package_id) if args.package_id else None,
            )
        )
        _print_json(result.report)
    return 0


def cmd_init_db(_: argparse.Namespace) -> int:
    init_database()
    print("Database initialized.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="blockchain-service")
    subparsers = parser.add_subparsers(dest="command", required=True)

    observe = subparsers.add_parser("observe-events", help="Observe provenance outbox events")
    observe.add_argument("--limit", type=int, default=100)
    observe.set_defaults(func=cmd_observe_events)

    process = subparsers.add_parser("process-anchor-requests", help="Build packages for pending requests")
    process.add_argument("--limit", type=int, default=100)
    process.set_defaults(func=cmd_process_anchor_requests)

    build = subparsers.add_parser("build-evidence-package", help="Build evidence package")
    build.add_argument("--event-id", dest="event_id")
    build.add_argument("--anchor-request-id", dest="anchor_request_id")
    build.set_defaults(func=cmd_build_evidence_package)

    simulate = subparsers.add_parser("simulate-anchoring", help="Simulate anchoring for package")
    simulate.add_argument("--package-id", required=True)
    simulate.add_argument("--network-code", default="local_simulated")
    simulate.set_defaults(func=cmd_simulate_anchoring)

    anchor = subparsers.add_parser("anchor-package", help="Anchor evidence package on selected network")
    anchor.add_argument("--package-id", required=True)
    anchor.add_argument("--network-code", default="local_simulated")
    anchor.set_defaults(func=cmd_anchor_package)

    query = subparsers.add_parser("query-anchor", help="Query on-chain anchored evidence")
    query.add_argument("--package-id", required=True)
    query.add_argument("--network-code", required=True)
    query.set_defaults(func=cmd_query_anchor)

    verify_anchor = subparsers.add_parser(
        "verify-anchor", help="Verify off-chain + on-chain evidence"
    )
    verify_anchor.add_argument("--package-id", required=True)
    verify_anchor.add_argument("--network-code", required=True)
    verify_anchor.set_defaults(func=cmd_verify_anchor)

    verify = subparsers.add_parser("verify-package", help="Verify evidence package integrity")
    verify.add_argument("--package-id", required=True)
    verify.set_defaults(func=cmd_verify_package)

    reprocess = subparsers.add_parser("reprocess-failed", help="Reprocess failed anchoring requests")
    reprocess.add_argument("--limit", type=int, default=50)
    reprocess.set_defaults(func=cmd_reprocess_failed)

    audit = subparsers.add_parser("audit-report", help="Generate audit report")
    audit.add_argument("--anchor-request-id")
    audit.add_argument("--package-id")
    audit.set_defaults(func=cmd_audit_report)

    init_db = subparsers.add_parser("init-db", help="Initialize local SQLite database")
    init_db.set_defaults(func=cmd_init_db)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
