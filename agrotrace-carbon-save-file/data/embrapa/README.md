# Dados Embrapa (grupo experimental 2)

## Papel na avaliação AgroMRV-Flow

A avaliação da arquitetura usa **dois grupos** de dados:

1. **Simulados (`FARM-*`)** — gerados por `save_file.emulated` com `--seed 42`.
2. **Embrapa** — este diretório: mensal `P-*` e anual `BR-*`.

Um terceiro grupo baseado em dados **diários** está fora do escopo da avaliação
atual (capacidade técnica permanece no código; não reintroduzir no seed demo).

## Arquivos versionados

| Arquivo | Descrição |
|---------|-----------|
| `annual_report.csv` | Inventário anual (fonte; `;` como delimitador) |
| `monthly_report.csv` | Relatório mensal (fonte) |
| `split.py` | Gera `annual/` e `monthly/` (um CSV por propriedade/período) |

As pastas `annual/` e `monthly/` são **geradas** e não precisam estar no Git:
o seed canônico (`frontend/scripts/reset_and_seed_pending_cycles.py`) e
`import_embrapa_uploads(ensure_split=True)` executam `split.py` automaticamente.

```bash
# Manual (opcional)
cd agrotrace-carbon-save-file
python data/embrapa/split.py
```

## Proveniência e redistribuição

- Os campos de proprietário/responsável nos CSVs usam valores anonimizados
  (`Anonymous`).
- Os arquivos são fornecidos **somente para fins acadêmicos** de reprodução
  da avaliação AgroMRV-Flow neste repositório.
- Redistribuição comercial ou republicação dos CSVs fora do contexto da
  dissertação requer autorização dos detentores dos dados originais e do
  autor do protótipo.
- A licença [LICENSE](../../../LICENSE) do software **não** concede direitos
  amplos sobre estes conjuntos de dados.

## Contagens de referência (após split)

- Mensal: 386 arquivos (`P-*`)
- Anual: 50 arquivos (`BR-*`, ano de inventário padrão 2022 no seed)
