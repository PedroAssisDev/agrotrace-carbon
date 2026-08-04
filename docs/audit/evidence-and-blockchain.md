# Evidências e blockchain

Gate: aprovação + publicação final (`is_blockchain_unlocked`).

O pacote usa hashes/ids do manifesto (sem payload sensível completo). Fluxo: observe → build evidence → simulate anchor → verify.

Merkle Root e verificação ficam no blockchain-service. Ancoragem é **simulada** (MVP).
