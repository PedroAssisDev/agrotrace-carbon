# calculation-service (ECOFARM / IPCC)

Calcula emissões de GEE por fazenda/período. Resultados são **preliminares** até
aprovação e publicação no frontend.

> Documento canônico do monorepo: [../docs/modules/calculation-service.md](../docs/modules/calculation-service.md)

## Responsabilidade

- Fórmulas IPCC/ECOFARM (entérica, dejetos, fertilizantes, energia, totais, intensidade)
- Exposição via `orchestration.pipeline.compute_farm_period_emissions`
- Sem persistência própria; sem HTTP

## Entrypoint usado pelo Dash

```python
from orchestration.pipeline import compute_farm_period_emissions
```

Adapter: `frontend/services/calculation_adapter.py`.

## Instalação

```bash
pip install -e ".[dev]"
# ou via tooling/install-workspace.ps1 na raiz do monorepo
```

## Testes

```bash
pytest
```

## Limitações

- Não publica nem ancora
- Não é fonte de predição
- Revisões técnicas históricas: `REVISAO_TECNICA_CALCULOS.md` (não é guia operacional)

## Relacionados

- Ciclo: etapa operacional `calculation` (`cycle_state`)
- Validadores FE: `validate_calculation_review`, `validate_preliminary_calculation_form`
