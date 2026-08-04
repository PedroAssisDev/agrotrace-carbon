// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {CarbonEvidenceRegistry} from "../src/CarbonEvidenceRegistry.sol";

contract CarbonEvidenceRegistryTest is Test {
    CarbonEvidenceRegistry internal registry;
    address internal owner = makeAddr("owner");
    address internal stranger = makeAddr("stranger");

    bytes32 internal evidenceKey = keccak256("pkg-uuid-1");
    bytes32 internal packageHash = bytes32(uint256(0x1111));
    bytes32 internal merkleRoot = bytes32(uint256(0x2222));

    event EvidenceAnchored(
        bytes32 indexed evidenceKey,
        bytes32 indexed packageHash,
        bytes32 merkleRoot,
        address indexed submitter,
        uint64 anchoredAt
    );

    function setUp() public {
        vm.prank(owner);
        registry = new CarbonEvidenceRegistry(owner);
    }

    function test_deploy_sets_owner() public view {
        assertEq(registry.owner(), owner);
    }

    function test_anchor_and_query() public {
        vm.warp(1_700_000_000);
        vm.prank(owner);
        registry.anchorEvidence(evidenceKey, packageHash, merkleRoot);

        (
            bytes32 storedPackageHash,
            bytes32 storedMerkleRoot,
            uint64 anchoredAt,
            address submitter,
            bool exists
        ) = registry.getEvidence(evidenceKey);

        assertTrue(exists);
        assertTrue(registry.evidenceExists(evidenceKey));
        assertEq(storedPackageHash, packageHash);
        assertEq(storedMerkleRoot, merkleRoot);
        assertEq(anchoredAt, 1_700_000_000);
        assertEq(submitter, owner);
    }

    function test_emits_event() public {
        vm.warp(1_700_000_123);
        vm.expectEmit(true, true, true, true);
        emit EvidenceAnchored(evidenceKey, packageHash, merkleRoot, owner, 1_700_000_123);
        vm.prank(owner);
        registry.anchorEvidence(evidenceKey, packageHash, merkleRoot);
    }

    function test_unauthorized_reverts() public {
        vm.prank(stranger);
        vm.expectRevert(CarbonEvidenceRegistry.NotAuthorized.selector);
        registry.anchorEvidence(evidenceKey, packageHash, merkleRoot);
    }

    function test_zero_evidence_key_reverts() public {
        vm.prank(owner);
        vm.expectRevert(CarbonEvidenceRegistry.ZeroEvidenceKey.selector);
        registry.anchorEvidence(bytes32(0), packageHash, merkleRoot);
    }

    function test_zero_package_hash_reverts() public {
        vm.prank(owner);
        vm.expectRevert(CarbonEvidenceRegistry.ZeroPackageHash.selector);
        registry.anchorEvidence(evidenceKey, bytes32(0), merkleRoot);
    }

    function test_zero_merkle_root_reverts() public {
        vm.prank(owner);
        vm.expectRevert(CarbonEvidenceRegistry.ZeroMerkleRoot.selector);
        registry.anchorEvidence(evidenceKey, packageHash, bytes32(0));
    }

    function test_overwrite_reverts() public {
        vm.startPrank(owner);
        registry.anchorEvidence(evidenceKey, packageHash, merkleRoot);
        vm.expectRevert(CarbonEvidenceRegistry.EvidenceAlreadyAnchored.selector);
        registry.anchorEvidence(evidenceKey, packageHash, merkleRoot);
        vm.stopPrank();
    }

    function test_query_missing_returns_empty() public view {
        (
            bytes32 storedPackageHash,
            bytes32 storedMerkleRoot,
            uint64 anchoredAt,
            address submitter,
            bool exists
        ) = registry.getEvidence(keccak256("missing"));

        assertFalse(exists);
        assertEq(storedPackageHash, bytes32(0));
        assertEq(storedMerkleRoot, bytes32(0));
        assertEq(anchoredAt, 0);
        assertEq(submitter, address(0));
    }
}
