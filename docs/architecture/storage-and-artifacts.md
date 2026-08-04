# Armazenamento e artefatos

| Armazenamento | Responsabilidade |
|---------------|------------------|
| `frontend/data/cycles/*.json` | Estado operacional atual do ciclo (UI/retomada) |
| `frontend/data/db/provenance.db` | Ledger de proveniência (tabelas ledger append-only; outbox/ops mutáveis — ver [append-only-tables.md](append-only-tables.md)) |
| `frontend/data/db/blockchain_service.db` | Pacotes, âncoras, verificações (`hash_record` / `verification_log` / `audit_log` append-only) |
| `agrotrace-carbon-save-file/data/originals/` | Arquivos brutos imutáveis |
| `frontend/data/normalized/` | Lotes normalizados |
| `frontend/data/ontology_exports/` | OWL/TTL exportados |
| `frontend/data/publications/` | Manifestos finais publicados |
| `frontend/data/evidence_packages/` | Pacotes de evidência |

Estado atual ≠ histórico: o JSON do ciclo não substitui o ledger de proveniência.
