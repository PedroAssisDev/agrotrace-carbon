# Armazenamento e artefatos

Todos os artefatos operacionais ficam sob a raiz de dados definida por
`AGROTRACE_DATA_ROOT` (padrão: `frontend/data/`). Esse diretório é isolável por ambiente
(ex.: temporário na regressão) e **ignorado pelo Git** — não versione dados operacionais.

## Diretórios e bancos

| Armazenamento | Responsabilidade |
|---------------|------------------|
| `cycles/*.json` | Estado operacional atual do ciclo (UI/retomada) |
| `db/provenance.db` | Ledger de proveniência (tabelas ledger append-only; outbox/ops mutáveis — ver [append-only-tables.md](append-only-tables.md)) |
| `db/blockchain_service.db` | Pacotes, âncoras, verificações (`hash_record` / `verification_log` / `audit_log` append-only) |
| `normalized/` | Lotes normalizados |
| `ontology_exports/` | OWL/TTL exportados (**gerado** — regenerável) |
| `publications/` | Manifestos finais publicados |
| `evidence_packages/` | Pacotes de evidência |
| `logs/` | Logs da aplicação |
| `agrotrace-carbon-save-file/data/originals/` | Arquivos brutos imutáveis (preservação) |
| `agrotrace-carbon-model-training-service/artifacts/` | Modelos treinados (**gerado**) |

## Tabelas principais

- Proveniência: ledger append-only de eventos + outbox/estado operacional mutável.
- Blockchain: `hash_record`, `verification_log`, `audit_log` (append-only).

## Regras

- Estado atual ≠ histórico: o JSON do ciclo **não** substitui o ledger de proveniência.
- Bancos, ciclos, ontologias publicadas, manifestos e pacotes de evidência **não** são
  removidos por rotinas de organização.
- Variáveis de ambiente (apenas nomes): `AGROTRACE_DATA_ROOT`, `AGROTRACE_LOG_LEVEL`,
  `AGROTRACE_LOG_FILE`. Ver [../development/data-directories.md](../development/data-directories.md).
