# Plano de evidências visuais — Capítulo 5

| # | Figura sugerida | Rota/aba | Requisito | Comprova | Não comprova |
|---|-----------------|----------|-----------|----------|--------------|
| F1 | Entrada de dados | `/data-entry` | RF001 | Contexto propriedade/período/layout | Integridade hash |
| F2 | Artefato bruto recuperado | `/technical-audit` → Artefatos | RF002 | Metadados + hash verificado | Ancoragem |
| F3 | Granularidade temporal | Painel/Indicadores filtro | RF005 | daily/monthly/annual na UI | Lot OWL |
| F4 | Explicabilidade de cálculo | `/calculations` detalhe | RF009 | fórmula/fatores/GWP | Qualidade científica IPCC |
| F5 | Correção e nova versão | `/approval` | RF010/RF014 | histórico de versões | Append-only DB |
| F6 | Predição separada | `/previsoes` | RF011 | estimativa ≠ publicado | Acurácia do modelo |
| F7 | Timeline proveniência | Auditoria → Timeline | RF006/RNF001 | linhagem | Blockchain |
| F8 | Blockchain bloqueada pré-pub | Auditoria → Blockchain | D7/RF019 | gate visual | Transação real |
| F9 | Metadados ancoragem sim/EVM | Blockchain + Integridade | RF019–021 | match hash/Merkle | Veracidade agropecuária |
| F10 | VersionManifest | Payload técnico | RNF010 | versões + missing_reason | Completude de todos os campos em todo ciclo |

## Roteiro de captura

1. Seed isolado ou ciclo de demonstração (não reset operacional sem backup).
2. Percorrer CE1→CE5 com um ciclo publicado + um em revisão.
3. Exportar PNG 1920×1080; legendas com cycle_id (não paths pessoais).
4. Anexar trecho de `_regressao.json` (pass/fail) como evidência tabular.
