// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {CarbonEvidenceRegistry} from "../src/CarbonEvidenceRegistry.sol";

/// @notice Deploy CarbonEvidenceRegistry. Owner defaults to the broadcaster.
contract DeployCarbonEvidenceRegistry is Script {
    function run() external returns (CarbonEvidenceRegistry registry) {
        address initialOwner = vm.envOr("DEPLOYER_ADDRESS", msg.sender);
        vm.startBroadcast();
        registry = new CarbonEvidenceRegistry(initialOwner);
        vm.stopBroadcast();
        console2.log("CarbonEvidenceRegistry deployed at", address(registry));
        console2.log("owner", initialOwner);
    }
}
