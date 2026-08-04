# CarbonEvidenceRegistry (Foundry)

Minimal Solidity registry for AgroTrace Carbon cryptographic evidence anchors.

## Commands

```bash
cd agrotrace-carbon-blockchain-service/contracts
forge install foundry-rs/forge-std --no-commit
forge fmt --check
forge build
forge test -vvv
```

## Local Anvil deploy

```bash
anvil
forge script script/DeployCarbonEvidenceRegistry.s.sol \
  --rpc-url http://127.0.0.1:8545 \
  --private-key <ANVIL_KEY> \
  --broadcast
```

## Sepolia deploy

```bash
forge script script/DeployCarbonEvidenceRegistry.s.sol \
  --rpc-url "$BLOCKCHAIN_SEPOLIA_RPC_URL" \
  --private-key "$BLOCKCHAIN_SEPOLIA_PRIVATE_KEY" \
  --broadcast
```

Never commit private keys. Export ABI with `python scripts/export_contract_abi.py`.
