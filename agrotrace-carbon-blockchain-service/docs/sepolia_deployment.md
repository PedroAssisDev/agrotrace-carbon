# Sepolia Deployment

## Configuration (names only)

```text
BLOCKCHAIN_SEPOLIA_RPC_URL
BLOCKCHAIN_SEPOLIA_CHAIN_ID=11155111
BLOCKCHAIN_SEPOLIA_PRIVATE_KEY
BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS
BLOCKCHAIN_SEPOLIA_CONFIRMATIONS
BLOCKCHAIN_SEPOLIA_REQUEST_TIMEOUT_SECONDS
BLOCKCHAIN_SEPOLIA_RECEIPT_TIMEOUT_SECONDS
BLOCKCHAIN_SEPOLIA_EXPLORER_BASE_URL
```

Copy `.env.example` → `.env` locally. Never commit secrets.

## Deploy

```bash
cd agrotrace-carbon-blockchain-service/contracts
forge script script/DeployCarbonEvidenceRegistry.s.sol \
  --rpc-url "$BLOCKCHAIN_SEPOLIA_RPC_URL" \
  --private-key "$BLOCKCHAIN_SEPOLIA_PRIVATE_KEY" \
  --broadcast
```

Update `contracts/deployments/sepolia.json` with real values after deploy (address, tx hash, block, deployer, timestamp). Do not invent values.

## Smoke test

```bash
python scripts/sepolia_smoke_test.py --package-id <UUID>
python scripts/sepolia_smoke_test.py --package-id <UUID> --query-only
```

## Automated tests

Sepolia tests are skipped by default:

```bash
# only when configured
set RUN_SEPOLIA_TESTS=1
python -m pytest tests/ -m sepolia
```
