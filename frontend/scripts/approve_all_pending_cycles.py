"""Aprova em massa todos os ciclos pendentes de aprovacao.

Para cada ciclo em PendingApproval:
  1. gera/garante calculation_review
  2. aprova todos os itens
  3. finalize_file_approval -> publicacao -> evidencias -> blockchain

Uso:
    python scripts/approve_all_pending_cycles.py --confirm
    python scripts/approve_all_pending_cycles.py --confirm --limit 10
    python scripts/approve_all_pending_cycles.py --confirm --property-prefix FARM-
    python scripts/approve_all_pending_cycles.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from services.blockchain_view_service import is_blockchain_unlocked  # noqa: E402
from services.bootstrap import bootstrap_all  # noqa: E402
from services.calculation_approval_service import (  # noqa: E402
    approve_item,
    approve_with_zero,
    finalize_file_approval,
)
from services.calculation_review_service import (  # noqa: E402
    ensure_calculation_review,
    list_review_items,
)
from services.cycle_status_service import (  # noqa: E402
    cycles_pending_approval,
    resolve_managerial_status,
)
from utils.file_helpers import list_cycles, save_cycle  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aprova em massa ciclos pendentes (publicacao + evidencias + blockchain)."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirma a aprovacao em massa (obrigatorio, exceto com --dry-run).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Lista ciclos que seriam aprovados, sem alterar dados.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limita a quantidade de ciclos processados (0 = todos).",
    )
    parser.add_argument(
        "--property-prefix",
        type=str,
        default="",
        help="Filtra por prefixo de property_id (ex.: FARM-, P-, BR-).",
    )
    parser.add_argument(
        "--property-id",
        type=str,
        default="",
        help="Filtra por property_id exato.",
    )
    parser.add_argument(
        "--reviewer",
        type=str,
        default="bulk-approve@agrotrace",
        help="Identidade do aprovador registrada na proveniencia.",
    )
    parser.add_argument(
        "--justification",
        type=str,
        default="Aprovacao em massa via approve_all_pending_cycles.py",
        help="Justificativa da aprovacao.",
    )
    return parser.parse_args()


def _approve_all_items(cycle: dict, *, reviewer: str) -> dict:
    cycle = ensure_calculation_review(cycle)
    for item in list_review_items(cycle):
        item_id = item["calculation_item_id"]
        if item.get("zero_assumptions"):
            cycle = approve_with_zero(
                cycle,
                item_id,
                reviewer=reviewer,
                justification="Zero assumido na aprovacao em massa.",
            )
        else:
            cycle = approve_item(
                cycle,
                item_id,
                reviewer=reviewer,
                justification="Item aprovado na aprovacao em massa.",
            )
    return cycle


def _select_pending(args: argparse.Namespace) -> list[dict]:
    pending = cycles_pending_approval(list_cycles())
    if args.property_id:
        pending = [c for c in pending if c.get("property_id") == args.property_id]
    elif args.property_prefix:
        prefix = args.property_prefix
        pending = [c for c in pending if str(c.get("property_id") or "").startswith(prefix)]
    pending = sorted(
        pending,
        key=lambda c: (c.get("property_id") or "", c.get("reporting_period") or "", c.get("cycle_id") or ""),
    )
    if args.limit and args.limit > 0:
        pending = pending[: args.limit]
    return pending


def main() -> int:
    args = _parse_args()
    if not args.dry_run and not args.confirm:
        print("Operacao destrutiva no sentido de avancar a pipeline: use --confirm.")
        print("Exemplo: python scripts/approve_all_pending_cycles.py --confirm")
        print("Dry-run: python scripts/approve_all_pending_cycles.py --dry-run")
        return 1

    bootstrap_all()
    pending = _select_pending(args)
    total = len(pending)
    print(f"Ciclos pendentes selecionados: {total}")
    if args.property_prefix:
        print(f"Filtro property-prefix: {args.property_prefix}")
    if args.property_id:
        print(f"Filtro property-id: {args.property_id}")
    if args.limit:
        print(f"Limite: {args.limit}")

    if total == 0:
        print("Nada a fazer.")
        return 0

    if args.dry_run:
        print("\n[DRY-RUN] Ciclos que seriam aprovados:")
        for i, cycle in enumerate(pending[:20], start=1):
            print(
                f"  {i}. {cycle.get('cycle_id')} | {cycle.get('property_id')} | "
                f"{cycle.get('reporting_period')}"
            )
        if total > 20:
            print(f"  ... e mais {total - 20}")
        return 0

    ok_count = 0
    fail_count = 0
    failures: list[str] = []

    for i, cycle in enumerate(pending, start=1):
        cid = cycle.get("cycle_id") or "?"
        pid = cycle.get("property_id") or "?"
        period = cycle.get("reporting_period") or "?"
        print(f"[{i}/{total}] Aprovando {cid} ({pid} / {period})...")
        try:
            cycle = _approve_all_items(cycle, reviewer=args.reviewer)
            cycle = finalize_file_approval(
                cycle,
                reviewer=args.reviewer,
                justification=args.justification,
            )
            save_cycle(cycle)
            st = resolve_managerial_status(cycle)
            unlocked = is_blockchain_unlocked(cycle)
            print(
                f"  OK status={st.key} blockchain_unlocked={unlocked} "
                f"evidence={bool(cycle.get('evidence_package'))}"
            )
            ok_count += 1
        except Exception as exc:  # noqa: BLE001 — continua nos demais ciclos
            fail_count += 1
            msg = f"{cid}: {exc}"
            failures.append(msg)
            print(f"  FAIL {msg}")
            traceback.print_exc()

    print("\n=== Resumo ===")
    print(f"Sucesso: {ok_count}")
    print(f"Falha:   {fail_count}")
    remaining = len(cycles_pending_approval(list_cycles()))
    print(f"Ainda pendentes no disco: {remaining}")
    if failures:
        print("\nFalhas:")
        for err in failures[:30]:
            print(f"  - {err}")
        if len(failures) > 30:
            print(f"  ... e mais {len(failures) - 30}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
