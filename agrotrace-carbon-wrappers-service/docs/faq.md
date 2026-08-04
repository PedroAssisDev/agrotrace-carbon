# FAQ técnica

## Qual é o contrato de saída oficial?

`ProcessingResult` é o contrato único do pipeline, usado tanto para integração quanto para observabilidade.

## Por que o separador de saída é `;_;` e não vírgula?

Vírgula e `;` aparecem frequentemente nos dados e em formatos europeus. Um separador raro e multi-caractere reduz colisões; a serialização customizada trata quoting correctamente.

## Posso usar extensão `.csv` nos ficheiros exportados?

Sim, configurando `file_extension=".csv"` em `ExportConfiguration`, desde que todos os consumidores saibam que o separador é `;_;` e não CSV RFC clássico.

## Como adiciono um layout sem alterar Python?

Quase tudo está no YAML. Se precisar de **nova** regra `ref` ou **nova** família de normalização, será necessário código.

## O que significa `source_schema_version`?

Hash derivado do documento YAML do layout (via JSON ordenado). Serve para rastrear qual definição foi usada. Alterações no YAML mudam o valor.

## Intradário e mensal usam o mesmo separador de entrada?

Não. Intradiário usa `,`. Mensal e anual usam `;` no ficheiro fonte.

## Onde fica a harmonização semântica avançada?

Passos declarados em `harmonization.steps` são aplicados em `normalizers.harmonization.apply_layout_harmonization`. Hoje existe a ref `strip_whitespace_strings`; outras refs exigem implementação de código (ver [harmonization.md](harmonization.md)).

## Pandas é obrigatório?

Consta em `requirements.txt`; o núcleo dos wrappers analisado não depende de Pandas directamente. Confirme no vosso ambiente se pode remover ou se outros módulos precisam.

## Como evito ambiguidade na deteção automática?

Afinar `detection.priority`, `min_score`, `min_column_count` e garantir cabeçalhos distintos entre layouts. Em dúvida, use `layout_id` explícito.

## Os testes cobrem ACV ou ontologia?

Não directamente. Testam pipeline, exportação, deteção e governança de manifest. Ontologia e unidades são extensões futuras.

## O que fazer com linhas rejeitadas?

Analisar `rejected_records` e `validation_report`, corrigir fonte, reprocessar. Ficheiros em `rejected/` espelham isso quando a exportação está activa.

Ver também: [README](README.md), [troubleshooting](troubleshooting.md).
