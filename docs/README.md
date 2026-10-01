# Documentação — AgroTrace Carbon

Mapa da documentação por público. Links relativos. Documentos arquivados **não** são
listados como atuais.

Status: `atual` = reflete o código; `gerado` = produzido por script (não editar à mão);
`histórico` = preservado, não representa o estado atual.

## Visão geral

| Documento | Finalidade | Público | Status |
|-----------|-----------|---------|--------|
| [architecture/overview.md](architecture/overview.md) | Visão geral e boundaries | todos | atual |
| [architecture/data-lifecycle.md](architecture/data-lifecycle.md) | Ciclo de vida do dado | todos | atual |
| [architecture/component-responsibilities.md](architecture/component-responsibilities.md) | O que cada componente faz e não faz | todos | atual |
| [architecture/result-state-model.md](architecture/result-state-model.md) | Estados do resultado e eventos | todos | atual |
| [limitations.md](limitations.md) | Implementado / simulado / preparado / ausente | todos | atual |
| [project-evolution.md](project-evolution.md) | Evolução com base em evidências | todos | atual |

## Desenvolvedor

| Documento | Finalidade | Status |
|-----------|-----------|--------|
| [development/setup.md](development/setup.md) | Instalação e execução | atual |
| [development/configuration.md](development/configuration.md) | Flags e variáveis | atual |
| [development/data-directories.md](development/data-directories.md) | Diretórios de dados | atual |
| [development/testing.md](development/testing.md) | Testes e regressão | atual |
| [development/validation-scripts.md](development/validation-scripts.md) | Scripts `validate_*` | atual |
| [development/reset-and-seed.md](development/reset-and-seed.md) | Reset e seed | atual |
| [development/troubleshooting.md](development/troubleshooting.md) | Problemas comuns | atual |
| [modules/](modules/) | Documento canônico por módulo (8) | atual |

## Pesquisador

| Documento | Finalidade | Status |
|-----------|-----------|--------|
| [academic/dissertation-alignment.md](academic/dissertation-alignment.md) | Precedência de fontes e alinhamento | atual |
| [academic/requirements.md](academic/requirements.md) | RF001–RF021, RNF001–RNF012 | atual |
| [academic/requirements-traceability.md](academic/requirements-traceability.md) | Requisito → código → teste → cenário | atual |
| [academic/evaluation-scenarios.md](academic/evaluation-scenarios.md) | CE1–CE5 | atual |
| [academic/evidence-guide.md](academic/evidence-guide.md) | Guia de evidências do Capítulo 5 | atual |

## Auditor

| Documento | Finalidade | Status |
|-----------|-----------|--------|
| [audits/current/](audits/current/) | Auditoria pós-implementação | atual / gerado |
| [audits/README.md](audits/README.md) | Auditoria atual vs histórica | atual |
| [architecture/security-and-integrity.md](architecture/security-and-integrity.md) | Integridade, hashes, Merkle, gates | atual |
| [evidence/README.md](evidence/README.md) | Ponteiros de evidência | atual |

## Operador

| Documento | Finalidade | Status |
|-----------|-----------|--------|
| [development/setup.md](development/setup.md) | Executar o protótipo | atual |
| [development/reset-and-seed.md](development/reset-and-seed.md) | Reset e seed | atual |
| [development/data-directories.md](development/data-directories.md) | `AGROTRACE_DATA_ROOT` | atual |

## Mantenedor

| Documento | Finalidade | Status |
|-----------|-----------|--------|
| [architecture/decisions/](architecture/decisions/) | ADRs | atual |
| [project-evolution.md](project-evolution.md) | Evolução e cleanup consolidado | atual |
| [maintenance/project-reorganization/](maintenance/project-reorganization/) | Inventário da reorganização | histórico |
| [archive/README.md](archive/README.md) | Material histórico | histórico |
| [audits/archive/](audits/archive/) | Auditorias antigas | histórico |
