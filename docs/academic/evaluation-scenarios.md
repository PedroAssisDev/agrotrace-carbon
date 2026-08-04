# Cenários de avaliação (CE1–CE5)

Cenários usados para avaliar a arquitetura na dissertação. O estado observado na última
auditoria fica em [../audits/current/05-cenarios-ce1-ce5.md](../audits/current/05-cenarios-ce1-ce5.md).

| CE | Cenário | Foco |
|----|---------|------|
| CE1 | Preparação e representação | Entrada, preservação, normalização, granularidade e proveniência inicial |
| CE2 | Cálculo e governança | Cálculo preliminar, revisão, correção, aprovação e publicação |
| CE3 | Predição | Estimativa preditiva separada do cálculo oficial e bloqueada na publicação |
| CE4 | Proveniência, evidências e integridade | Pacote de evidências, canonicalização, Merkle, ancoragem e verificação |
| CE5 | Visualização e auditoria | Painel, indicadores e auditoria técnica (8 rotas, 9 abas) |

## Limitações declaradas

- CE1 e CE2 estão **parcialmente** atendidos na última auditoria (classe `Lot` ausente na
  OWL; dois validadores de cálculo/detalhe falham).
- CE4: a rede Sepolia não foi reexecutada na última auditoria; a evidência é documental
  (deployment e validação interativa preexistentes).
- CE5: capturas visuais do Capítulo 5 ainda pendentes.

Estas limitações são preservadas como observadas — a reorganização não as trata como
resolvidas.
