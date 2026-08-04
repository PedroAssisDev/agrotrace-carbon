# agrotrace-carbon-save-file

Servico de preservacao do dado bruto original do AgroTrace Carbon.

## Papel no ciclo

Cobre as etapas iniciais de entrada e preservacao:

1. Salvar o arquivo original em pasta controlada (`data/originals/`).
2. Calcular o SHA-256 do arquivo original.
3. Produzir os metadados (source artifact) que a proveniencia precisa.

O arquivo salvo aqui e depois consumido pelo wrappers-service. Este servico
**nao** faz normalizacao, calculo, registro de proveniencia nem ancoragem
blockchain — apenas preserva o original e devolve seus metadados.

## Integracao

Chamada direta a funcao Python (sem HTTP), no padrao do prototipo:

```python
from save_file import save_original_content, retrieve_original

meta = save_original_content(
    b"...",
    property_id="FARM-001",
    reporting_period="2026-01",
    original_filename="entrada.csv",
)
# meta -> artifact_id, original_filename, stored_path, sha256, file_size_bytes,
#         file_extension, uploaded_at, property_id, reporting_period, source_system

original = retrieve_original(artifact_id=meta["artifact_id"])
# original.content, original_filename, content_type, size, uploaded_at,
# artifact_id, registered_sha256, recomputed_sha256, verification_status
```

Recuperacao (RF002) e feita por `artifact_id` (preferencial) ou `sha256` (legado).
A API **nao** aceita caminho arbitrario do usuario; o path e resolvido apenas
dentro do storage root, com verificacao de containment e rehash SHA-256.

No frontend a integracao passa por `frontend/services/save_file_adapter.py`
(`save_*`, `retrieve_original`, `retrieve_by_cycle_id`, `to_ui_dto`), com
fallback explicito. A UI nao deve exibir caminhos absolutos.

## Estrutura

- `save_file/storage.py`: salvamento, recuperacao e metadados.
- `save_file/models.py`: `RetrievedOriginal`.
- `save_file/errors.py`: erros de dominio (ausencia, meta, escape, divergencia).
- `save_file/hashing.py`: SHA-256 de arquivo e de bytes.
- `save_file/emulated/`: geração de CSVs simulados realistas (sem emissões pré-calculadas).
- `data/emulated_uploads/`: staging regenerável (`emulated_*.csv` + `manifest.json`).
- `data/originals/`: arquivos originais preservados após upload/import.

## Testes

```bash
cd agrotrace-carbon-save-file
python -m unittest tests.test_retrieve_original tests.test_emulated_generation
```


## Dados emulados

Gerar arquivos (Fase A — sem pipeline):

```bash
# Fase A — gerar CSVs
cd agrotrace-carbon-save-file
python scripts/generate_emulated_uploads.py --seed 42

# Fase B — reset + import pela pipeline real
cd frontend
python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42
python scripts/validate_emulated_import.py
python scripts/validate_pending_approval_seed.py
```

Importar pela pipeline do frontend (Fase B):

```bash
cd ../frontend
python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42
```

Os CSVs **não** contêm colunas de emissão (`enteric_tCO2e`, `ef_enteric_kgCH4`); o cálculo ocorre na pipeline via `calculation-service`.
