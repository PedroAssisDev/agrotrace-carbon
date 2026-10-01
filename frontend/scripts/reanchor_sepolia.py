"""Reancora na Sepolia ciclos oficiais com pacote ainda simulado.

Uso:
    python scripts/reanchor_sepolia.py --property-id P-18
    python scripts/reanchor_sepolia.py --property-id P-18 --dry-run
    python scripts/reanchor_sepolia.py --property-id P-18 --limit 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = FRONTEND_ROOT.parent
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(WORKSPACE_ROOT / ".env", override=False)
    load_dotenv(FRONTEND_ROOT / ".env", override=False)
    load_dotenv(WORKSPACE_ROOT / "agrotrace-carbon-blockchain-service" / ".env", override=True)
except ImportError:
    pass


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reancora pacotes simulados na Ethereum Sepolia.")
    p.add_argument("--property-id", default="P-18", help="Filtra por property_id.")
    p.add_argument("--dry-run", action="store_true", help="Lista elegíveis sem ancorar.")
    p.add_argument("--limit", type=int, default=0, help="Limite de ciclos (0 = todos).")
    return p.parse_args()


def _needs_sepolia(cycle: dict) -> bool:
    if not (cycle.get("evidence_package") or {}).get("evidence_package_id"):
        return False
    anchoring = cycle.get("anchoring") or {}
    evidence = cycle.get("evidence_package") or {}
    network = anchoring.get("network") or evidence.get("network") or ""
    kind = anchoring.get("anchoring_kind") or ""
    if network == "ethereum_sepolia" and kind != "SIMULADA" and anchoring.get("explorer_url"):
        return False
    return True


def main() -> int:
    args = _parse_args()
    from services.blockchain_view_service import is_blockchain_unlocked
    from services.bootstrap import bootstrap_all
    from services import local_orchestrator
    from utils.file_helpers import list_cycles, save_cycle
    import config

    bootstrap_all()
    print(f"network={config.BLOCKCHAIN_DEFAULT_NETWORK_CODE}")

    cycles = [
        c for c in list_cycles()
        if str(c.get("property_id") or "") == args.property_id
        and is_blockchain_unlocked(c)
        and _needs_sepolia(c)
    ]
    cycles.sort(key=lambda c: str(c.get("reporting_period") or ""))
    if args.limit > 0:
        cycles = cycles[: args.limit]

    print(f"elegíveis={len(cycles)} property={args.property_id}")
    if args.dry_run:
        for c in cycles:
            anc = c.get("anchoring") or {}
            print(
                f"  {c.get('cycle_id')} period={c.get('reporting_period')} "
                f"net={anc.get('network')} kind={anc.get('anchoring_kind')}"
            )
        return 0

    ok = 0
    fail = 0
    for c in cycles:
        cid = c.get("cycle_id")
        print(f"--- anchoring {cid} ---")
        try:
            updated = local_orchestrator.run_anchoring_step(c)
            save_cycle(updated)
            anc = updated.get("anchoring") or {}
            print(
                f"OK {cid} net={anc.get('network')} kind={anc.get('anchoring_kind')} "
                f"status={anc.get('anchoring_status')}"
            )
            print(f"  tx={anc.get('transaction_id')}")
            print(f"  explorer={anc.get('explorer_url')}")
            if anc.get("network") == "ethereum_sepolia" and anc.get("explorer_url"):
                ok += 1
            else:
                fail += 1
                print(f"  WARN unexpected result for {cid}")
        except Exception as exc:  # noqa: BLE001
            fail += 1
            print(f"FAIL {cid}: {exc}")

    print(f"done ok={ok} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
