"""Shared constants for blockchain service."""

CANONICALIZATION_METHOD_V1 = "json_canonical_v1"
HASH_ALGORITHM_SHA256 = "sha256"
MERKLE_STRATEGY_V1 = "merkle_strategy_v1"
SCHEMA_VERSION_EVIDENCE_ITEM = "evidence_item_v1"
SCHEMA_VERSION_EVIDENCE_PACKAGE = "evidence_package_v1"
SCHEMA_VERSION_ANCHOR_PAYLOAD = "anchor_payload_v1"

ELIGIBLE_ANCHOR_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "CALCULATION_APPROVED",
        "MONTHLY_RESULT_CONSOLIDATED",
        "ANNUAL_RESULT_CONSOLIDATED",
        "APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY",
        "DAILY_DATA_AGGREGATED_TO_MONTHLY",
        "MONTHLY_DATA_AGGREGATED_TO_ANNUAL",
    }
)

EVENT_TO_PACKAGE_TYPE: dict[str, str] = {
    "CALCULATION_APPROVED": "annual_carbon_result",
    "MONTHLY_RESULT_CONSOLIDATED": "monthly_carbon_result",
    "ANNUAL_RESULT_CONSOLIDATED": "annual_carbon_result",
    "APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY": "ontology_publication",
    "DAILY_DATA_AGGREGATED_TO_MONTHLY": "daily_to_monthly_aggregation",
    "MONTHLY_DATA_AGGREGATED_TO_ANNUAL": "monthly_to_annual_aggregation",
}

EVENT_TO_REQUEST_SCOPE: dict[str, str] = {
    "CALCULATION_APPROVED": "annual",
    "MONTHLY_RESULT_CONSOLIDATED": "monthly",
    "ANNUAL_RESULT_CONSOLIDATED": "annual",
    "APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY": "manual",
    "DAILY_DATA_AGGREGATED_TO_MONTHLY": "aggregation",
    "MONTHLY_DATA_AGGREGATED_TO_ANNUAL": "aggregation",
}
