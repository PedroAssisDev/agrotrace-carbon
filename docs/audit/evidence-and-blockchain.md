# Evidências e blockchain

Gate: aprovação + publicação final (`is_blockchain_unlocked`), ou seja
`FINAL_ONTOLOGY_PUBLISHED`.

O pacote de evidências usa hashes/ids do manifesto (sem payload sensível completo).
Fluxo: observe → build evidence → anchor → verify.

Merkle Root e verificação ficam no blockchain-service. A ancoragem tem provider
**simulado por padrão** (`local_simulated`, sem chave privada) e provider **EVM** opcional
(Anvil local / Sepolia). Não é "apenas simulada".

Ver [../architecture/security-and-integrity.md](../architecture/security-and-integrity.md)
e [../modules/blockchain-service.md](../modules/blockchain-service.md).
