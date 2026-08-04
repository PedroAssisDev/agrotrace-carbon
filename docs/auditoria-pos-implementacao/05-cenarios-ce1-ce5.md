# Cenários CE1–CE5

Cap. 5 **não está redigido** no PDF; cenários seguem o plano de avaliação do Cap. 4 + prompt da auditoria.

| ID | Cenário | Status | Evidência |
|----|---------|--------|-----------|
| CE1 | Preparacao e representacao | PARCIALMENTE ATENDIDO | pipeline+temporal OK; Lot OWL ausente; recuperacao bruto OK |
| CE2 | Calculo e governanca | PARCIALMENTE ATENDIDO | revisao/correcao/aprovacao/publicacao OK; 2 validate de calculo/detalhe FAILam |
| CE3 | Predicao | ATENDIDO | separacao e bloqueio de publicacao demonstrados |
| CE4 | Proveniencia, evidencias e integridade | ATENDIDO | pacote+canonical+Merkle+provider simulado+idempotencia; Sepolia nao reexecutada |
| CE5 | Visualizacao e auditoria | ATENDIDO | validate_technical_audit; evidencias visuais Cap.5 ainda pendentes |

## Contagem
`{"PARCIALMENTE ATENDIDO": 2, "ATENDIDO": 3}`

## Procedimento

1. `python frontend/scripts/run_full_regression.py --out docs/auditoria-pos-implementacao/_regressao.json`
2. Ambiente: TemporaryDirectory + `AGROTRACE_DATA_ROOT`
3. Provider blockchain: simulado / Forge local (sem Sepolia)

## Limitações

- CE1: Lot não modelado como classe OWL.
- CE2: falhas em detalhe de emissão (série por gás) e formulário preliminar (factor_catalog).
- CE4: ancoragem EVM pública não reexecutada.
- CE5: operabilidade via scripts; screenshots Cap. 5 ainda necessários.
