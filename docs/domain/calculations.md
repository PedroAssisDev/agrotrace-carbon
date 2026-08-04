# Cálculos

Fonte oficial das fórmulas: `agrotrace-carbon-calculation-service` (`orchestration.pipeline.compute_farm_period_emissions`).

Cobertura típica: fermentação entérica, manejo de dejetos, fertilizantes, energia, totais CO₂e e intensidade.

O frontend monta parâmetros (entradas, fatores, GWP explícito via `emissions.defaults.gwp_ipcc_ar4`) e registra o resultado preliminar com hash. Não aplica GWP silencioso por default local do FE.

Resultados permanecem preliminares até aprovação e publicação do manifesto.
