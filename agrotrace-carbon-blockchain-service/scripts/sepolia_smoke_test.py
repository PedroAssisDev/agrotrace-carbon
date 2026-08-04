"""Sepolia smoke test — runs only with explicit configuration.

Usage:
  python scripts/sepolia_smoke_test.py --package-id <UUID>
  python scripts/sepolia_smoke_test.py --package-id <UUID> --query-only
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass

from app.application.container import ServiceContainer, init_database
from app.application.dto.commands import (
    AnchorEvidencePackageCommand,
    QueryAnchoredEvidenceCommand,
    VerifyAnchoredEvidenceCommand,
)
from app.application.use_cases.anchor_evidence_package import AnchorEvidencePackageUseCase
from app.application.use_cases.query_anchored_evidence import QueryAnchoredEvidenceUseCase
from app.application.use_cases.verify_anchored_evidence import VerifyAnchoredEvidenceUseCase
from app.shared.constants import NETWORK_CODE_ETHEREUM_SEPOLIA
from app.shared.ids import ensure_uuid


def _to_jsonable(obj: object) -> object:
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    return obj


def main() -> int:
    parser = argparse.ArgumentParser(description="Sepolia anchoring smoke test")
    parser.add_argument("--package-id", required=True)
    parser.add_argument("--query-only", action="store_true")
    args = parser.parse_args()

    container = ServiceContainer()
    settings = container.settings
    if not settings.sepolia_ready():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "Sepolia not configured",
                    "required": [
                        "BLOCKCHAIN_SEPOLIA_RPC_URL",
                        "BLOCKCHAIN_SEPOLIA_PRIVATE_KEY",
                        "BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS",
                        "BLOCKCHAIN_SEPOLIA_CHAIN_ID=11155111",
                    ],
                },
                indent=2,
            )
        )
        return 2

    init_database(settings)
    package_id = ensure_uuid(args.package_id)
    account = None
    try:
        from eth_account import Account

        key = settings.sepolia_private_key
        key_hex = key if key.startswith("0x") else "0x" + key
        account = Account.from_key(key_hex).address
    except Exception:
        account = None

    print(
        json.dumps(
            {
                "network_code": NETWORK_CODE_ETHEREUM_SEPOLIA,
                "chain_id": settings.sepolia_chain_id,
                "contract_address": settings.sepolia_contract_address,
                "wallet_address": account,
                "rpc_configured": bool(settings.sepolia_rpc_url),
            },
            indent=2,
        )
    )

    with container.unit_of_work() as uow:
        if args.query_only:
            result = QueryAnchoredEvidenceUseCase(uow, container.providers).execute(
                QueryAnchoredEvidenceCommand(
                    evidence_package_id=package_id,
                    network_code=NETWORK_CODE_ETHEREUM_SEPOLIA,
                )
            )
            print(json.dumps(_to_jsonable(result), indent=2, default=str))
            return 0

        anchor = AnchorEvidencePackageUseCase(uow, container.providers).execute(
            AnchorEvidencePackageCommand(
                evidence_package_id=package_id,
                network_code=NETWORK_CODE_ETHEREUM_SEPOLIA,
            )
        )
        query = QueryAnchoredEvidenceUseCase(uow, container.providers).execute(
            QueryAnchoredEvidenceCommand(
                evidence_package_id=package_id,
                network_code=NETWORK_CODE_ETHEREUM_SEPOLIA,
            )
        )
        verify = VerifyAnchoredEvidenceUseCase(uow, container.providers).execute(
            VerifyAnchoredEvidenceCommand(
                evidence_package_id=package_id,
                network_code=NETWORK_CODE_ETHEREUM_SEPOLIA,
            )
        )
        print(
            json.dumps(
                {
                    "anchor": _to_jsonable(anchor),
                    "query": _to_jsonable(query),
                    "verify": _to_jsonable(verify),
                },
                indent=2,
                default=str,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
