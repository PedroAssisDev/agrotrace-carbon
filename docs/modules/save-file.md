# Módulo: save-file

## Finalidade

Preservar o arquivo bruto de origem de forma imutável e permitir sua recuperação, com
integridade por SHA-256.

## Responsabilidades

- Salvar o original e calcular seu hash SHA-256 (integridade off-chain).
- Recuperar o original por identificador ou por hash.

## Não faz

- Não normaliza, não calcula, não ancora. O hash do arquivo bruto **não** é ancoragem blockchain.

## Contratos com o frontend

- `save_original_file`, `save_original_content` (escrita).
- `save_file/storage.py::retrieve_original` (leitura).
- Adapter: `frontend/services/save_file_adapter`.

## Entradas / saídas / persistência

- Entrada: conteúdo/arquivo bruto.
- Saída: registro do original + SHA-256.
- Persistência: `agrotrace-carbon-save-file/data/originals/` (imutável).

## Compatibilidade legada

Recuperação aceita `sha256` além de `artifact_id` (documentada no README do serviço) — preservar.

## Testes e comandos

- Suíte unittest do pacote (`python -m unittest discover -s tests`), incluída na regressão.

## Relacionados

- RF002; RNF001, RNF004.
- Detalhe: `agrotrace-carbon-save-file/README.md`.
- Ver [../architecture/security-and-integrity.md](../architecture/security-and-integrity.md).
