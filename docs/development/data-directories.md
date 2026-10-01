# Diretórios de dados

Todos os artefatos operacionais ficam sob `AGROTRACE_DATA_ROOT` (padrão `frontend/data/`),
ignorado pelo Git. Para isolar um ambiente (ex.: testes), aponte a variável para um
diretório temporário.

## Layout

```text
$AGROTRACE_DATA_ROOT/
├── cycles/            # estado operacional dos ciclos (*.json)
├── properties/        # registro de fazendas/propriedades
├── db/                # provenance.db, blockchain_service.db
├── normalized/        # lotes normalizados
├── ontology/          # exports OWL/TTL de trabalho
├── ontology_exports/  # OWL/TTL (gerado, regenerável)
├── publications/      # manifestos finais publicados
├── evidence_packages/ # pacotes de evidência
├── model_training/    # artefatos/registry quando sob data root
└── logs/              # logs da aplicação
```

Originais preservados ficam em `agrotrace-carbon-save-file/data/originals/` (ou sob
`$AGROTRACE_DATA_ROOT/save_file/originals/` conforme configuração) e modelos treinados
podem residir em `agrotrace-carbon-model-training-service/artifacts/` ou sob
`$AGROTRACE_DATA_ROOT/model_training/`.

Definido em: `frontend/config.py` (`DATA_DIR`, `PROPERTIES_DIR`, etc.).

## Variáveis de ambiente (apenas nomes)

- `AGROTRACE_DATA_ROOT` — raiz dos artefatos operacionais.
- `AGROTRACE_LOG_LEVEL`, `AGROTRACE_LOG_FILE` — logging.
- `PROV_DATABASE_URL`, `BLOCKCHAIN_DATABASE_URL`, `BLOCKCHAIN_PROVENANCE_DATABASE_URL` —
  normalmente derivadas pelo bootstrap a partir de `AGROTRACE_DATA_ROOT`.

Aviso: não versione nem apague manualmente bancos, ciclos, ontologias publicadas,
manifestos ou pacotes de evidência. Ver
[../architecture/storage-and-artifacts.md](../architecture/storage-and-artifacts.md).
