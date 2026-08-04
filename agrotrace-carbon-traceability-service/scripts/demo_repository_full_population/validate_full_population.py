"""Functional validation of demo full population."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from demo_config import (  # noqa: E402
    DEMO_PREFIX,
    FARM_BOA_VISTA,
    FARM_SANTA_CLARA,
    FARM_SAO_PEDRO,
    RUN_CODE_ANNUAL,
    RUN_CODE_REVISION,
    YEAR,
    create_session_stack,
    ensure_local_database,
)
from demo_data import (  # noqa: E402
    BOA_VISTA_ANNUAL_TOTAL,
    BOA_VISTA_MONTHLY_MILK_LITERS,
    REVISION_JANUARY_V2,
    SANTA_CLARA_DAILY_MILK_LITERS,
    SANTA_CLARA_JANUARY_DAYS,
)
from demo_ids import run_code_annual_boa_vista, run_code_annual_santa, run_code_monthly  # noqa: E402
from demo_tables import EXPECTED_TABLES  # noqa: E402
from provenance_service.domain.shared.enums import (  # noqa: E402
    CalculationResultSetStatus,
    CalculationReviewDecision,
)
from provenance_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    tag = "[OK]" if ok else "[FAIL]"
    msg = f"{tag} {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    if not ok:
        FAILURES.append(name if not detail else f"{name}: {detail}")


def _demo_runs(uow):
    runs, _ = uow.pipeline_runs.list_filtered(limit=500, offset=0)
    return [r for r in runs if r.run_code.startswith(DEMO_PREFIX)]


def _count_table(uow, table: str) -> int:
    from sqlalchemy import text

    session = uow.session
    return int(session.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0)


def _agg_used_count(uow, pipeline_run_id, activity_name: str) -> int:
    from provenance_service.infrastructure.db.models.prov_core import ProvActivityModel
    from sqlalchemy import select

    session = uow.session
    act = session.scalar(
        select(ProvActivityModel).where(
            ProvActivityModel.pipeline_run_id == pipeline_run_id,
            ProvActivityModel.name == activity_name,
        )
    )
    if act is None:
        return 0
    return len(uow.prov_relations.list_used_by_activity(act.activity_id))


def main() -> int:
    ensure_local_database()
    _, sf, _ = create_session_stack()

    with SqlAlchemyUnitOfWork(sf) as uow:
        demo_runs = _demo_runs(uow)
        check("1_pipeline_runs_exist", len(demo_runs) >= 4, f"count={len(demo_runs)}")

        empty_tables = [t for t in EXPECTED_TABLES if _count_table(uow, t) == 0]
        check(
            "2_all_expected_tables_populated",
            not empty_tables,
            f"empty={empty_tables}" if empty_tables else f"{len(EXPECTED_TABLES)} tables",
        )

        annual_run = uow.pipeline_runs.get_by_run_code(RUN_CODE_ANNUAL)
        check("3_annual_direct_run", annual_run is not None)
        if annual_run:
            bundles = uow.prov_bundles.list_by_pipeline_run(annual_run.pipeline_run_id)
            check("4_bundles_per_annual_run", len(bundles) >= 1, f"{len(bundles)} bundles")
            entities = [
                e
                for b in bundles
                for e in uow.prov_entities.list_by_bundle(b.bundle_id)
            ]
            check("5_prov_entities", len(entities) >= 1)
            activities = [
                a
                for b in bundles
                for a in uow.prov_activities.list_by_bundle(b.bundle_id)
            ]
            check("6_prov_activities", len(activities) >= 1)
            check("7_prov_agents", _count_table(uow, "prov_core_prov_agent") >= 3)

            used_total = _count_table(uow, "prov_core_prov_used")
            gen_total = _count_table(uow, "prov_core_prov_generated")
            der_total = _count_table(uow, "prov_core_prov_derived_from")
            assoc_total = _count_table(uow, "prov_core_prov_associated_with")
            check("8_prov_used", used_total > 0)
            check("9_prov_generated", gen_total > 0)
            check("10_prov_derived_from", der_total > 0)
            check("11_prov_associated_with", assoc_total > 0)

            v2_run = uow.pipeline_runs.get_by_run_code(f"{RUN_CODE_REVISION}-v2")
            rev_count = (
                len(uow.prov_relations.list_revisions_for_pipeline_run(v2_run.pipeline_run_id))
                if v2_run
                else 0
            )
            check("12_prov_revision_reprocessing", rev_count >= 1, f"{rev_count} revisions")

            check(
                "13_prov_attributes",
                _count_table(uow, "prov_core_prov_attribute") > 0,
            )
            check(
                "14_source_artifact_revisions",
                _count_table(uow, "pipeline_source_artifact_revision") >= 2,
            )
            check(
                "15_wrapper_definitions",
                _count_table(uow, "pipeline_wrapper_definition") >= 1,
            )
            check(
                "16_wrapper_executions",
                _count_table(uow, "pipeline_wrapper_execution") > 0,
            )
            check(
                "17_normalized_batches",
                _count_table(uow, "pipeline_normalized_batch") > 0,
            )
            check(
                "18_semantic_integrations",
                _count_table(uow, "semantic_semantic_integration_execution") > 0,
            )
            check(
                "19_canonical_snapshots",
                _count_table(uow, "semantic_canonical_snapshot") > 0,
            )
            check(
                "20_canonical_snapshot_items",
                _count_table(uow, "semantic_canonical_snapshot_item") > 0,
            )
            check(
                "21_ontology_resource_links",
                _count_table(uow, "semantic_ontology_resource_link") > 0,
            )
            check(
                "22_calculation_methods",
                _count_table(uow, "calculation_calculation_method") >= 1,
            )
            check(
                "23_calculation_method_versions",
                _count_table(uow, "calculation_calculation_method_version") >= 1,
            )
            check(
                "24_parameter_sets",
                _count_table(uow, "calculation_calculation_parameter_set") > 0,
            )
            check(
                "25_parameter_values",
                _count_table(uow, "calculation_calculation_parameter_value") > 0,
            )
            check(
                "26_calculation_executions",
                _count_table(uow, "calculation_calculation_execution") > 0,
            )
            check(
                "27_result_sets",
                _count_table(uow, "calculation_calculation_result_set") > 0,
            )
            check(
                "28_result_items",
                _count_table(uow, "calculation_calculation_result_item") > 0,
            )
            check(
                "29_calculation_reviews",
                _count_table(uow, "calculation_calculation_review") > 0,
            )
            check(
                "30_publication_executions",
                _count_table(uow, "calculation_result_publication_execution") > 0,
            )
            check("31_hash_records", _count_table(uow, "audit_hash_record") > 0)
            check(
                "32_blockchain_anchors",
                _count_table(uow, "audit_blockchain_anchor") > 0,
            )
            check("33_audit_events", _count_table(uow, "audit_audit_event") > 0)
            check("34_outbox_events", _count_table(uow, "audit_outbox_event") > 0)

            # Case-specific
            annual_aggs = [
                a
                for a in activities
                if a.name in ("annual_aggregation", "monthly_aggregation_january")
            ]
            check(
                "35_annual_direct_no_aggregation",
                annual_run.farm_reference == FARM_SAO_PEDRO
                and not any(
                    a.name == "annual_aggregation"
                    for b in uow.prov_bundles.list_by_pipeline_run(annual_run.pipeline_run_id)
                    for a in uow.prov_activities.list_by_bundle(b.bundle_id)
                ),
            )

            bv_annual = uow.pipeline_runs.get_by_run_code(run_code_annual_boa_vista())
            if bv_annual:
                n_used = _agg_used_count(uow, bv_annual.pipeline_run_id, "annual_aggregation")
                check(
                    "36_monthly_annual_aggregation_12_inputs",
                    n_used == 12,
                    f"used={n_used}",
                )
                items = []
                for rs in uow.calculation_result_sets.list_by_pipeline_run(
                    bv_annual.pipeline_run_id
                ):
                    items.extend(uow.calculation_result_sets.list_items(rs.calculation_result_set_id))
                total = sum(
                    (i.result_value for i in items if i.result_name == "aggregated_milk_production"),
                    Decimal(0),
                )
                check(
                    "37_boa_vista_annual_total_150500",
                    total == BOA_VISTA_ANNUAL_TOTAL,
                    f"got {total}",
                )

            sc_jan_agg = uow.pipeline_runs.get_by_run_code(
                "demo_repo_santa_clara_2026-m01-agg"
            )
            if sc_jan_agg:
                n_daily = _agg_used_count(
                    uow, sc_jan_agg.pipeline_run_id, "monthly_aggregation_january"
                )
                check(
                    "38_daily_monthly_jan_31_inputs",
                    n_daily == SANTA_CLARA_JANUARY_DAYS,
                    f"used={n_daily}",
                )

            sc_annual = uow.pipeline_runs.get_by_run_code(run_code_annual_santa())
            if sc_annual:
                n_monthly = _agg_used_count(
                    uow, sc_annual.pipeline_run_id, "annual_aggregation"
                )
                check(
                    "39_santa_annual_12_monthly_inputs",
                    n_monthly == 12,
                    f"used={n_monthly}",
                )

            published_ok = True
            hash_ok = True
            anchor_ok = True
            for run in demo_runs:
                pubs = uow.result_publication_executions.list_by_pipeline_run(
                    run.pipeline_run_id
                )
                for pub in pubs:
                    rs = uow.calculation_result_sets.get(pub.calculation_result_set_id)
                    if rs is None:
                        published_ok = False
                        continue
                    if rs.result_set_status is not CalculationResultSetStatus.APPROVED:
                        published_ok = False
                    reviews = uow.calculation_reviews.list_for_result_set(
                        rs.calculation_result_set_id
                    )
                    if not any(
                        r.decision is CalculationReviewDecision.APPROVED for r in reviews
                    ):
                        published_ok = False
                    hr = uow.hash_records.find_by_subject(
                        "calculation_result_set",
                        rs.calculation_result_set_id,
                        "sha256",
                    )
                    if hr is None:
                        hash_ok = False
                    else:
                        anchors = uow.blockchain_anchors.list_by_pipeline_run(
                            run.pipeline_run_id
                        )
                        if not any(a.hash_record_id == hr.hash_record_id for a in anchors):
                            anchor_ok = False

            check(
                "40_published_have_approval_hash_anchor",
                published_ok and hash_ok and anchor_ok,
                f"pub_ok={published_ok} hash_ok={hash_ok} anchor_ok={anchor_ok}",
            )

            monthly_count = sum(
                1
                for r in demo_runs
                if r.farm_reference == FARM_BOA_VISTA
                and r.reporting_period_reference in {f"{YEAR}-{m:02d}" for m in range(1, 13)}
            )
            check(
                "extra_12_boa_vista_monthly_runs",
                monthly_count >= 12,
                f"monthly_runs={monthly_count}",
            )

    print(f"\nValidações: {40 - len(FAILURES)}/40 OK, {len(FAILURES)} falhas")
    if FAILURES:
        print("Falhas:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
