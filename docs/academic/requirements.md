# Requisitos (RF001–RF021, RNF001–RNF012)

Numeração oficial da dissertação. Este documento lista apenas os requisitos (título e
descrição resumida); o estado de atendimento vive na
[auditoria atual](../audits/current/03-matriz-requisitos.md) e a rastreabilidade em
[requirements-traceability.md](requirements-traceability.md).

**Fonte:** dissertação (arquivo `frontend/main (7).pdf`), capítulos 4–5. Estrutura
derivada de `docs/audits/current/09-resultados.json` (fonte alinhada ao PDF).
A validação automática de IDs está em `frontend/scripts/validate_requirements_ids.py`.

## Requisitos funcionais (RF)

| ID | Requisito |
|----|-----------|
| RF001 | Entrada de dados agropecuários |
| RF002 | Preservação e recuperação dos dados brutos |
| RF003 | Normalização e padronização |
| RF004 | Validação de qualidade e consistência |
| RF005 | Granularidades temporal e organizacional |
| RF006 | Registro de proveniência |
| RF007 | Ontologia de trabalho |
| RF008 | Cálculo preliminar |
| RF009 | Registro dos parâmetros de cálculo |
| RF010 | Correção, recálculo e nova versão |
| RF011 | Predição de emissões e produção |
| RF012 | Métricas e indicadores |
| RF013 | Revisão humana |
| RF014 | Decisão individual sobre cada cálculo |
| RF015 | Aprovação geral do ciclo |
| RF016 | Publicação da ontologia final |
| RF017 | Pacote de evidências |
| RF018 | Identificadores criptográficos |
| RF019 | Ancoragem em blockchain |
| RF020 | Visualização e auditoria técnica |
| RF021 | Consulta e verificação de evidência |

## Requisitos não funcionais (RNF)

| ID | Requisito |
|----|-----------|
| RNF001 | Rastreabilidade |
| RNF002 | Auditabilidade |
| RNF003 | Manutenibilidade |
| RNF004 | Integridade |
| RNF005 | Explicabilidade |
| RNF006 | Consistência semântica |
| RNF007 | Operabilidade das interfaces |
| RNF008 | Extensibilidade |
| RNF009 | Reprodutibilidade |
| RNF010 | Versionamento |
| RNF011 | Interoperabilidade |
| RNF012 | Proteção de credenciais e minimização on-chain |

> A numeração anterior em `requirements_map.yaml` (arquivada em
> [`../audits/archive/2026-08-03-capitulo-5/`](../audits/archive/2026-08-03-capitulo-5/README.md))
> diverge do PDF e **não** deve ser usada como fonte atual.
