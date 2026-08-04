// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title CarbonEvidenceRegistry
/// @notice Minimal immutable registry for cryptographic evidence anchors.
/// @dev Stores only hashes/metadata. Never stores business payloads or PII.
contract CarbonEvidenceRegistry {
    struct AnchorRecord {
        bytes32 packageHash;
        bytes32 merkleRoot;
        uint64 anchoredAt;
        address submitter;
        bool exists;
    }

    address public immutable owner;
    mapping(bytes32 => AnchorRecord) private records;

    error NotAuthorized();
    error ZeroEvidenceKey();
    error ZeroPackageHash();
    error ZeroMerkleRoot();
    error EvidenceAlreadyAnchored();

    event EvidenceAnchored(
        bytes32 indexed evidenceKey,
        bytes32 indexed packageHash,
        bytes32 merkleRoot,
        address indexed submitter,
        uint64 anchoredAt
    );

    constructor(address initialOwner) {
        require(initialOwner != address(0), "owner=0");
        owner = initialOwner;
    }

    function anchorEvidence(bytes32 evidenceKey, bytes32 packageHash, bytes32 merkleRoot) external {
        if (msg.sender != owner) revert NotAuthorized();
        if (evidenceKey == bytes32(0)) revert ZeroEvidenceKey();
        if (packageHash == bytes32(0)) revert ZeroPackageHash();
        if (merkleRoot == bytes32(0)) revert ZeroMerkleRoot();
        if (records[evidenceKey].exists) revert EvidenceAlreadyAnchored();

        uint64 anchoredAt = uint64(block.timestamp);
        records[evidenceKey] = AnchorRecord({
            packageHash: packageHash,
            merkleRoot: merkleRoot,
            anchoredAt: anchoredAt,
            submitter: msg.sender,
            exists: true
        });

        emit EvidenceAnchored(evidenceKey, packageHash, merkleRoot, msg.sender, anchoredAt);
    }

    function getEvidence(bytes32 evidenceKey)
        external
        view
        returns (
            bytes32 packageHash,
            bytes32 merkleRoot,
            uint64 anchoredAt,
            address submitter,
            bool exists
        )
    {
        AnchorRecord storage record = records[evidenceKey];
        return
            (
                record.packageHash,
                record.merkleRoot,
                record.anchoredAt,
                record.submitter,
                record.exists
            );
    }

    function evidenceExists(bytes32 evidenceKey) external view returns (bool) {
        return records[evidenceKey].exists;
    }
}
