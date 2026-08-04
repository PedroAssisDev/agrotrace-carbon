"""Configuração central do frontend AgroTrace Carbon."""

from __future__ import annotations

from pathlib import Path

# ── Diretórios ──────────────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = FRONTEND_DIR.parent

DATA_DIR = FRONTEND_DIR / "data"
RAW_ORIGINALS_DIR = DATA_DIR / "raw_originals"
NORMALIZED_DIR = DATA_DIR / "normalized"
ONTOLOGY_DIR = DATA_DIR / "ontology"
ONTOLOGY_EXPORTS_DIR = DATA_DIR / "ontology_exports"
EVIDENCE_PACKAGES_DIR = DATA_DIR / "evidence_packages"
PUBLICATIONS_DIR = DATA_DIR / "publications"
REPORTS_DIR = DATA_DIR / "reports"
CYCLES_DIR = DATA_DIR / "cycles"
PROPERTIES_DIR = DATA_DIR / "properties"
DB_DIR = DATA_DIR / "db"

PROV_DB_PATH = DB_DIR / "provenance.db"
BLOCKCHAIN_DB_PATH = DB_DIR / "blockchain_service.db"

# Serviços existentes (somente leitura/import)
SAVE_FILE_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-save-file"
SAVE_FILE_ORIGINALS_DIR = SAVE_FILE_SERVICE_DIR / "data" / "originals"
SAVE_FILE_EMULATED_UPLOADS_DIR = SAVE_FILE_SERVICE_DIR / "data" / "emulated_uploads"
SAVE_FILE_EMBRAPA_DIR = SAVE_FILE_SERVICE_DIR / "data" / "embrapa"
SAVE_FILE_EMBRAPA_MONTHLY_DIR = SAVE_FILE_EMBRAPA_DIR / "monthly"
SAVE_FILE_EMBRAPA_ANNUAL_DIR = SAVE_FILE_EMBRAPA_DIR / "annual"
WRAPPERS_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-wrappers-service"
CALCULATION_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-calculation-service"
ONTOLOGY_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-ontology-manager"
BLOCKCHAIN_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-blockchain-service"
TRACEABILITY_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-traceability-service"
TRACEABILITY_SRC_DIR = TRACEABILITY_SERVICE_DIR / "src"
MODEL_TRAINING_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-model-training-service"
MODEL_TRAINING_ARTIFACTS_DIR = MODEL_TRAINING_SERVICE_DIR / "artifacts"
MODEL_REGISTRY_PATH = MODEL_TRAINING_ARTIFACTS_DIR / "registry.jsonl"
MODEL_TRAINING_CONFIG_PATH = MODEL_TRAINING_SERVICE_DIR / "configs" / "training.yaml"
MODEL_TRAINING_SRC_DIR = MODEL_TRAINING_SERVICE_DIR / "src"

# Assets do workspace (referência, sem mover)
AUTH_BACKGROUNDS_DIR = WORKSPACE_ROOT / "auth_backgrounds"
LOGO_DIR = WORKSPACE_ROOT / "logo"
LOGO_PATH = LOGO_DIR / "Logo.png"

# CSV de exemplo no workspace
SAMPLE_DATA_DIR = WORKSPACE_ROOT / "data"

# ── Modos de integração ─────────────────────────────────────────────────────
# USE_MOCK_DATA: força mocks apenas em caminhos de teste explícitos (não no runtime normal).
# USE_DIRECT_FUNCTION_CALLS: integra via chamadas Python diretas (sem HTTP).
# ALLOW_MOCK_FALLBACK: se True, falhas de serviço viram mock silencioso — PROIBIDO no fluxo real.
USE_MOCK_DATA = False
USE_DIRECT_FUNCTION_CALLS = True
ALLOW_MOCK_FALLBACK = False

# ── Identidade visual ───────────────────────────────────────────────────────
# PRESENTATION_MODE: ativa CSS de prints (sem debug menu, sombras suaves, payload claro).
PRESENTATION_MODE = True

APP_TITLE = "AgroTrace Carbon"
APP_SUBTITLE = (
    "Plataforma para gestão, cálculo e acompanhamento de emissões agropecuárias"
)

# ── Layouts de wrapper ──────────────────────────────────────────────────────
LAYOUT_OPTIONS = {
    "intraday": "intraday:v1",
    "monthly": "monthly:v1",
    "annual": "annual:v1",
}

# Status / eventos / etapas: fonte canônica em services.domain_catalog
# (listas duplicadas removidas desta config).

# ── Dash server ─────────────────────────────────────────────────────────────
DASH_HOST = "127.0.0.1"
DASH_PORT = 8050
DEBUG = True

# Blockchain network for anchoring (local_simulated | anvil_local | ethereum_sepolia)
# Prefer BLOCKCHAIN_DEFAULT_NETWORK_CODE env; never default to Sepolia without config.
import os as _os

BLOCKCHAIN_DEFAULT_NETWORK_CODE = _os.environ.get(
    "BLOCKCHAIN_DEFAULT_NETWORK_CODE", "local_simulated"
)

# Logging: AGROTRACE_LOG_LEVEL (default DEBUG), AGROTRACE_LOG_FILE → utils/logging_config.py


def ensure_data_dirs() -> None:
    """Cria pastas de dados do protótipo se não existirem."""
    for d in (
        RAW_ORIGINALS_DIR,
        SAVE_FILE_ORIGINALS_DIR,
        SAVE_FILE_EMULATED_UPLOADS_DIR,
        NORMALIZED_DIR,
        ONTOLOGY_DIR,
        ONTOLOGY_EXPORTS_DIR,
        EVIDENCE_PACKAGES_DIR,
        PUBLICATIONS_DIR,
        REPORTS_DIR,
        CYCLES_DIR,
        PROPERTIES_DIR,
        DB_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
