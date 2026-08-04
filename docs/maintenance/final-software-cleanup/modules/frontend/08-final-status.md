# 08-final-status.md

Status: **PROJETO PRONTO COM LIMITAÇÕES**

## Resumo

O frontend Dash (`agrotrace-carbon-frontend` v1.0.0) possui `pyproject.toml` fino com deps alinhadas a `requirements.txt`, `.gitignore` local e `__version__` em `config.py`.

## Entregas desta fase

| Item | Estado |
|------|--------|
| `frontend/.gitignore` | Criado — `.env`, `data/**` (com `.gitkeep`), caches, venv |
| `frontend/pyproject.toml` v1.0.0 | Criado (`requires-python >=3.11`) |
| `requirements.txt` | Mantido como referência canônica de deps Dash |
| `__version__ = "1.0.0"` | `frontend/config.py` |
| Testes (`pytest tests/ -q --tb=line`) | Ver `results.json` |

## Limitações conhecidas (fase legado posterior)

- **`LEGACY_REDIRECTS`** em `frontend/pages/router.py` permanece até a fase de remoção de legado (rotas antigas → `/technical-audit` etc.).
- **`YEARLY` / `process_file_auto`** não alterados nesta fase (cleanup posterior).
- Serviços irmãos (wrappers, cálculo, ontologia, proveniência, blockchain) continuam instalados separadamente ou via PYTHONPATH conforme `bootstrap.py`.

## Instalação e testes

```bash
cd frontend
python -m venv .venv-test
.venv-test\Scripts\activate
pip install -r requirements.txt
pip install -e .
pytest tests/ -q --tb=line
```

## Validação registrada

Consulte `results.json` para timestamp, contagem de testes e exit code.
