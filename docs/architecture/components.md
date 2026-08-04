# Componentes

| Pacote | Papel | Contrato principal com o FE |
|--------|-------|------------------------------|
| save-file | Preservar original | `save_original_file` / `save_original_content` |
| wrappers | Normalizar layouts | `process_file` |
| ontology-manager | OWL + validação | `build_full_ontology`, `populate_from_dataframe`, `validate_all` |
| calculation-service | Emissões | `compute_farm_period_emissions`, `FarmPeriodInput`, `gwp_ipcc_ar4` |
| traceability-service | Proveniência | `ProvenanceRecorder`, UoW |
| blockchain-service | Evidência / Merkle / verify | use cases observe/build/anchor/verify |

Frontend: páginas em `frontend/pages/`, callbacks em `frontend/callbacks/`, adapters e view services em `frontend/services/`.
