# Granularidades temporal e organizacional

## Temporal (canônico interno)

`daily` | `monthly` | `annual`

Aliases de leitura (`yearly`, `anual`, `mensal`, `intraday`, …) são normalizados em `services.domain_catalog`. Na interface, use rótulos em português.

O calculation-service mantém `TemporalScope.YEARLY` internamente; o adapter mapeia `annual` ↔ `yearly`.

## Organizacional (canônico interno)

`animal` → `lot` → `property`

Campo `organizational_granularity` no ciclo/manifesto. IDs: `property_id` (canônico; UI “fazenda”), `lot_id` opcional, `animal_id` opcional. Agregações devem ser explícitas e rastreáveis.
