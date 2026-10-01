# Módulo: save-file

## Visão geral

Preservar o arquivo bruto de origem de forma imutável e permitir recuperação, com
integridade por SHA-256.

**Posição:** etapa operacional `raw_data` (com hash e registro de proveniência).

## Responsabilidades

- Salvar original + SHA-256 (integridade **off-chain**)
- Recuperar por `artifact_id` (preferencial) ou `sha256` (legado)

## Não faz

- Não normaliza, não calcula, não ancora
- Hash do bruto **≠** ancoragem blockchain

## Contratos

- `save_original_file`, `save_original_content`, `retrieve_original`
- Adapter: `frontend/services/save_file_adapter.py` (fallback local explícito se import falhar)

Implementado em: `agrotrace-carbon-save-file/save_file/storage.py`.

## Entradas / saídas / persistência

- Persistência: `agrotrace-carbon-save-file/data/originals/` (ou sob data root)
- Dados auxiliares: `data/emulated_uploads/`, `data/embrapa/` (CSVs fonte + `split.py`)

## Testes

`python -m unittest discover -s tests` (incluído na regressão);
`validate_emulated_import`.

## Relacionados

- RF002; RNF001, RNF004
- README: `agrotrace-carbon-save-file/README.md`
- [../architecture/security-and-integrity.md](../architecture/security-and-integrity.md)
