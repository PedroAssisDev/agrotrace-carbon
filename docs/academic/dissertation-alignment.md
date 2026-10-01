# Alinhamento com a dissertação

## Precedência de fontes

Para resolver divergências, use esta ordem:

1. Dissertação (LaTeX/PDF) — fonte oficial de RF001–RF021, RNF001–RNF012, decisões
   arquiteturais e CE1–CE5.
2. Código e testes atuais — fonte da implementação real.
3. ADRs ([../architecture/decisions/](../architecture/decisions/)) — decisões consolidadas.
4. Schemas, contratos, ontologias e migrações — contratos técnicos.
5. Auditoria pós-implementação mais recente ([../audits/current/](../audits/current/)) — evidências.
6. Documentação atual — alinhada às fontes acima.
7. Documentação histórica — não prevalece sobre as fontes atuais.

## Estado da fonte oficial

O PDF/LaTeX da dissertação (`frontend/main (7).pdf`) **não está versionado** no
repositório. Enquanto isso, a estrutura de requisitos usada como referência alinhada ao
PDF é `docs/audits/current/09-resultados.json`. Quando o PDF entrar no repositório,
revalide os requisitos e a rastreabilidade.

## Divergência conhecida

`requirements_map.yaml` (arquivado em
[`../audits/archive/2026-08-03-capitulo-5/`](../audits/archive/2026-08-03-capitulo-5/README.md))
usa numeração de RF divergente do PDF (ex.: RF004, RF006, RF007). O PDF prevalece; o mapa
antigo é insumo histórico do gerador `frontend/scripts/generate_audit_reports.py` e não
deve ser citado como atual. A validação `frontend/scripts/validate_requirements_ids.py`
impede IDs fora de RF001–RF021 / RNF001–RNF012 / CE1–CE5 na fonte alinhada.

## Nomenclatura

- Termos temporais: `daily`, `monthly`, `annual`. `yearly` é apenas alias legado de leitura.
- Organizacional: `animal`, `lot`, `property`.
- Resultado: preliminar → em revisão → aprovado/rejeitado → publicado.
- "AgroTrace Carbon" é o nome técnico de pastas/artefatos; no texto, use "arquitetura
  proposta para MRV agropecuário".
