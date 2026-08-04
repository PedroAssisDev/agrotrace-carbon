"""Shared constants for blockchain service."""

CANONICALIZATION_METHOD_V1 = "json_canonical_v1"
HASH_ALGORITHM_SHA256 = "sha256"
MERKLE_STRATEGY_V1 = "merkle_strategy_v1"
SCHEMA_VERSION_EVIDENCE_ITEM = "evidence_item_v1"
SCHEMA_VERSION_EVIDENCE_PACKAGE = "evidence_package_v1"
SCHEMA_VERSION_ANCHOR_PAYLOAD = "anchor_payload_v1"

# Only final ontology publication unlocks anchoring (ADR-003 / FINAL_ONTOLOGY_PUBLISHED gate).
# Aliases represent the same milestone across frontend and provenance outbox naming.
ELIGIBLE_ANCHOR_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "FINAL_ONTOLOGY_PUBLISHED",
        "APPROVED_RESULT_PUBLISHED",
        "APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY",
    }
)

FINAL_PUBLICATION_EVENT_TYPES: frozenset[str] = ELIGIBLE_ANCHOR_EVENT_TYPES

EVENT_TO_PACKAGE_TYPE: dict[str, str] = {
    "FINAL_ONTOLOGY_PUBLISHED": "ontology_publication",
    "APPROVED_RESULT_PUBLISHED": "ontology_publication",
    "APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY": "ontology_publication",
}

EVENT_TO_REQUEST_SCOPE: dict[str, str] = {
    "FINAL_ONTOLOGY_PUBLISHED": "manual",
    "APPROVED_RESULT_PUBLISHED": "manual",
    "APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY": "manual",
}

NETWORK_CODE_LOCAL_SIMULATED = "local_simulated"
NETWORK_CODE_ANVIL_LOCAL = "anvil_local"
NETWORK_CODE_ETHEREUM_SEPOLIA = "ethereum_sepolia"

SUPPORTED_NETWORK_CODES: frozenset[str] = frozenset(
    {
        NETWORK_CODE_LOCAL_SIMULATED,
        NETWORK_CODE_ANVIL_LOCAL,
        NETWORK_CODE_ETHEREUM_SEPOLIA,
    }
)
