# Anvil Local Validation

## Prerequisites

- Foundry (`forge`, `anvil`) on PATH
- Python deps including `web3`

## Steps

```bash
# Terminal 1
anvil --host 127.0.0.1 --port 8545 --chain-id 31337

# Terminal 2
cd agrotrace-carbon-blockchain-service/contracts
forge build
forge create src/CarbonEvidenceRegistry.sol:CarbonEvidenceRegistry \
  --rpc-url http://127.0.0.1:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
  --constructor-args 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
  --broadcast

# Export ABI
cd ..
python scripts/export_contract_abi.py

# Configure
set BLOCKCHAIN_ANVIL_RPC_URL=http://127.0.0.1:8545
set BLOCKCHAIN_ANVIL_CONTRACT_ADDRESS=<deployed address>
set BLOCKCHAIN_DEFAULT_NETWORK_CODE=anvil_local

# Automated tests (starts its own Anvil)
python -m pytest tests/integration/test_anvil_anchoring.py -m blockchain_local -vv

# CLI
python -m app.interfaces.cli anchor-package --package-id <UUID> --network-code anvil_local
python -m app.interfaces.cli query-anchor --package-id <UUID> --network-code anvil_local
python -m app.interfaces.cli verify-anchor --package-id <UUID> --network-code anvil_local
```

Anvil private key above is the well-known local account #0 — never use it on Sepolia or mainnet.
