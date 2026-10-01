# Verificação Git e dados

## Git — inicial

- Branch: `master`
- Commits: 0
- HEAD: inexistente
- Status: todo o tree untracked (`??`)

## Git — final

- Mesmo estado (auditoria **não** criou commit nem alterou código de produção).
- Artefatos novos sob `docs/auditoria-pos-implementacao/` (relatórios).

## Inventário operacional — hashes

| Arquivo | SHA-256 antes | SHA-256 depois | Match |
|---------|---------------|----------------|-------|
| frontend/data/db/blockchain_service.db | C0B9CAFF…A2645 | C0B9CAFF…A2645 | sim |
| frontend/data/db/provenance.db | E8CB58F9…CD1C8 | 42BAFB2F…572AF | **não** |

### Nota sobre `provenance.db`

1. Imediatamente após a regressão isolada, o hash ainda coincidia com o baseline.
2. Em verificação posterior, o hash mudou e o tamanho cresceu (26 308 608 → 26 341 376 bytes); `provenance.db-wal` / `-shm` que existiam no inventário inicial **desapareceram**.
3. Interpretação mais provável: **checkpoint SQLite** (merge do WAL preexistente no arquivo principal), não escrita intencional da suíte de auditoria em `frontend/data/`.
4. A regressão usou `TemporaryDirectory` + `AGROTRACE_DATA_ROOT`; `blockchain_service.db` operacional permaneceu idêntico.
5. Limitação: sem commit Git e com WAL ativo no início, não há prova criptográfica absoluta de que nenhum processo externo tocou a proveniência operacional durante a janela.

## Ambiente temporário

- Criado por `tempfile.TemporaryDirectory` dentro de `run_full_regression.py`
- Removido ao fim do processo
- Nenhum `reset_test_environment.py` / wipe operacional

## Arquivos produzidos pela auditoria

- `docs/auditoria-pos-implementacao/00-…` a `10-…`
- `docs/auditoria-pos-implementacao/_regressao.json`
- `docs/auditoria-pos-implementacao/09-resultados.json`
- auxiliares: `_gen_reports.py`

## Confirmação

- `blockchain_service.db` operacional: **inalterado**.
- `provenance.db` operacional: **hash alterado** (ver nota WAL acima) — declarar como limitação.
- Testes de regressão direcionados ao root temporário.
Gerado em: 2026-08-04T13:34:02.916823+00:00
