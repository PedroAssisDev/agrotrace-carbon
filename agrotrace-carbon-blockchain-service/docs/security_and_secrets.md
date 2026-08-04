# Security and Secrets

## Rules

- Never commit `.env`, private keys, mnemonics, or RPC URLs with embedded tokens
- Never log private keys or signed raw transactions
- Never put secrets in frontend code or JSON manifests
- On-chain data is limited to cryptographic evidence (hashes + metadata)
- Anvil default keys are for local development only
- Do not use production wallets or funded mainnet keys

## Safe files

- `.env.example` — placeholders only
- `contracts/deployments/sepolia.json` — public addresses/tx hashes only after real deploy
- ABI JSON — public contract interface

## Wallet handling

Private keys are loaded from environment into memory for signing and are not persisted by the service.
