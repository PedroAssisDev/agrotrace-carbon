# Troubleshooting

## Layout não identificado (process_file_auto)

Sintomas: excepção `LayoutDetectionError` ou `detect_layout_id` devolve `None`.

Causas: cabeçalho não satisfaz nenhum layout; delimitador errado; ficheiro vazio; pontuação abaixo do limiar.

Diagnóstico: ver a primeira linha não vazia; comparar com `layouts/*/v1/layout.yaml` (aliases, `detection`).

Correcção: usar `layout_id` explícito; corrigir o CSV; ajustar `detection` no YAML sem criar ambiguidade.

## Schema incompatível

Sintomas: muitos campos vazios ou rejeição em massa.

Causas: ficheiro de outro layout; encoding ou nomes de coluna incorrectos.

Diagnóstico: chaves da primeira linha após leitura CSV.

Correcção: corrigir fonte ou definir novo layout com aliases.

## Campo obrigatório ausente

Sintomas: código `MISSING_REQUIRED_FIELD` no relatório.

Correcção: acrescentar coluna ou alinhar alias no YAML.

## Erro de parsing estrutural

Sintomas: `FAILURE`, `STRUCTURAL_PARSE_ERROR`, flag `parse_failure`.

Causas: ficheiro inexistente, permissões, encoding, CSV corrupto.

Correcção: validar path e encoding.

## Erro de normalização

Sintomas: `_reject_phase` igual a `normalization`.

Causas comuns intradiário: falta de data parseável (`_parsed_date`).

Correcção: corrigir datas na origem.

## Falha de exportação

Sintomas: excepção ao escrever ficheiros.

Causas: `base_dir` sem permissão.

Correcção: permissões ou outro caminho.

## Delimitador exportado `;_;`

Sintomas: colunas partidas ao abrir no Excel ou com parser CSV clássico.

Correcção: usar `read_delimited_table` do pacote ou importar com separador multi-caractere consciente.

## Rejeição parcial

Sintomas: `partial_success` e ficheiros em `rejected/`.

Correcção: inspeccionar `validation_report` e `rejected_records`; corrigir linhas ou fluxo de quarentena.

## Testes pytest

Import `wrappers` falha: executar a partir do directorio pai de `wrappers` ou instalar o pacote.

Testes V1 skipped: criar `wrappers/data` com CSV esperados ou aceitar skip.

## Layout não registado

Sintomas: `KeyError` no registry.

Correcção: `layout.yaml` em `layouts/` com `layout_id` único; reiniciar processo.

## layout_id duplicado

Sintomas: warning no log do registry.

Correcção: um único YAML por `layout_id`.

Ver também: [faq](faq.md), [registry-and-versioning](registry-and-versioning.md).
