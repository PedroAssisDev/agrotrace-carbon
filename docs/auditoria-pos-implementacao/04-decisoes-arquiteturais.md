# Decisões arquiteturais (Cap. 4.2.3)

**Nota oficial ([Extract PDF RF/RNF criteria](39359bd8-6283-440a-9a5a-86f4c740a3cd)):** a seção **4.2.3** lista **9** decisões nomeadas. O item de “publicação vinculada à aprovação” pertence à seção **4.5.10** (não a 4.2.3). O “frontend orquestrador” é cláusula da decisão 1 (separação de responsabilidades), não uma 10ª decisão de 4.2.3.

## D1–D9 — Cap. 4.2.3 (oficiais)

| ID | Decisão | Status | Evidência |
|----|---------|--------|-----------|
| D1 | Separação de responsabilidades (frontend orquestra sem absorver lógica interna) | ATENDIDO | serviços + adapters; chamada Python direta |
| D2 | Separação entre os estados dos resultados | ATENDIDO | preliminar/revisão/aprovado/rejeitado/publicado; correção é evento |
| D3 | Separação entre cálculo e predição | ATENDIDO | `PredictionNotPublishableError` |
| D4 | Separação entre proveniência e blockchain | ATENDIDO | gate `FINAL_ONTOLOGY_PUBLISHED`; DBs distintos |
| D5 | Abstração dos providers de ancoragem | ATENDIDO | `BlockchainAnchorProviderPort`; Simulated + EVM |
| D6 | Canonicalização única dos pacotes | ATENDIDO | `json_canonical_v1` no blockchain-service; frontend fail-closed |
| D7 | Gate de publicação final | ATENDIDO | `is_blockchain_unlocked`; full cycle |
| D8 | Idempotência e proibição de sobrescrita | ATENDIDO | forge overwrite; chave `SHA-256(network:hash)` |
| D9 | Minimização dos registros on-chain | ATENDIDO | contrato só key/hash/merkle/owner/time |

### Contagem Cap. 4.2.3
`{"ATENDIDO": 9}`

## Complementar — Cap. 4.5.10

| ID | Decisão | Status | Evidência |
|----|---------|--------|-----------|
| D10* | Publicação vinculada ao fluxo de aprovação (não tela independente de publicação final) | ATENDIDO | `publication_service` a partir de aprovação; rota dedicada de “publicar” ausente |

\*Identificador auxiliar do prompt de auditoria; **não** é o 10º item de 4.2.3.

## Violações / riscos

- Nenhuma violação estrutural grave (HTTP entre front e serviços locais, ancoragem pré-publicação, ou predição publicada) foi observada nos testes executados.
- **Atenção:** `ui_preview_hash` em `hash_helpers.py` usa `json.dumps` — permitido só para preview; hashes oficiais fail-closed.
- Frontend lê proveniência SQLite em modo RO (`provenance_query_service`); blockchain **não** via `sqlite3` direto — via adapter/bootstrap ([Static audit 6.x blocks](a436cf5b-2f65-4876-9ce6-bd984bdf9a07)).
- `jsonschema` está em optional-dependencies `dev` do blockchain-service (risco de coleta se `[dev]` não instalado).
