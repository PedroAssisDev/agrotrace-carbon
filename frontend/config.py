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
WRAPPERS_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-wrappers-service"
CALCULATION_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-calculation-service"
ONTOLOGY_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-ontology-manager"
BLOCKCHAIN_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-blockchain-service"
TRACEABILITY_SERVICE_DIR = WORKSPACE_ROOT / "agrotrace-carbon-traceability-service"
TRACEABILITY_SRC_DIR = TRACEABILITY_SERVICE_DIR / "src"

# Assets do workspace (referência, sem mover)
AUTH_BACKGROUNDS_DIR = WORKSPACE_ROOT / "auth_backgrounds"
LOGO_DIR = WORKSPACE_ROOT / "logo"
LOGO_PATH = LOGO_DIR / "Logo.png"

# CSV de exemplo no workspace
SAMPLE_DATA_DIR = WORKSPACE_ROOT / "data"

# ── Modos de integração ─────────────────────────────────────────────────────
# USE_MOCK_DATA: força o uso de dados simulados em todo o frontend.
# USE_DIRECT_FUNCTION_CALLS: integra via chamadas Python diretas (sem HTTP).
# ALLOW_MOCK_FALLBACK: quando uma chamada real falha, permite cair em mock.
#   Se False, o erro é propagado para a lista de erros do ciclo e exibido na UI.
USE_MOCK_DATA = False
USE_DIRECT_FUNCTION_CALLS = True
ALLOW_MOCK_FALLBACK = True

# ── Identidade visual ───────────────────────────────────────────────────────
# PRESENTATION_MODE: ativa CSS de prints (sem debug menu, sombras suaves, payload claro).
PRESENTATION_MODE = True

APP_TITLE = "AgroTrace Carbon"
APP_SUBTITLE = (
    "Plataforma para gestão, cálculo e acompanhamento de emissões agropecuárias"
)

# ── GWP padrão (IPCC AR4) ───────────────────────────────────────────────────
DEFAULT_GWP = {"CH4": 25.0, "N2O": 298.0, "CO2": 1.0}

# ── Layouts de wrapper ──────────────────────────────────────────────────────
LAYOUT_OPTIONS = {
    "intraday": "intraday:v1",
    "monthly": "monthly:v1",
    "annual": "annual:v1",
}

# ── Status do ciclo ─────────────────────────────────────────────────────────
CYCLE_STATUSES = [
    "DRAFT",
    "RAW_DATA_REGISTERED",
    "ORIGINAL_FILE_STORED",
    "WRAPPER_SELECTED",
    "WRAPPER_EXECUTED",
    "NORMALIZED_BATCH_CREATED",
    "NORMALIZED_DATA_REVIEWED",
    "CANONICAL_MODEL_POPULATED",
    "CANONICAL_PUBLISHED",
    "SEMANTIC_VALIDATION_RUNNING",
    "SEMANTIC_VALIDATION_FAILED",
    "SEMANTIC_VALIDATION_APPROVED",
    "CALCULATION_RUNNING",
    "CALCULATION_PRELIMINARY_RESULT_CREATED",
    "AWAITING_HUMAN_APPROVAL",
    "CALCULATION_APPROVED",
    "FINAL_ONTOLOGY_PUBLICATION_PENDING",
    "FINAL_ONTOLOGY_PUBLISHED",
    "EVIDENCE_PACKAGE_CREATED",
    "LOCAL_HASH_CREATED",
    "ANCHOR_REQUEST_CREATED",
    "ANCHORING_PENDING",
    "ANCHORING_SIMULATED",
    "ANCHORED",
    "VERIFICATION_PENDING",
    "VERIFIED",
    "VERIFICATION_FAILED",
]

# ── Eventos de proveniência ─────────────────────────────────────────────────
PROVENANCE_EVENT_TYPES = [
    "RAW_DATA_REGISTERED",
    "ORIGINAL_FILE_STORED",
    "WRAPPER_EXECUTED",
    "NORMALIZED_BATCH_CREATED",
    "SEMANTIC_MAPPING_COMPLETED",
    "CANONICAL_PUBLISHED",
    "SEMANTIC_VALIDATION_COMPLETED",
    "CALCULATION_PRELIMINARY_RESULT_CREATED",
    "CALCULATION_APPROVED",
    "FINAL_ONTOLOGY_PUBLISHED",
    "EVIDENCE_PACKAGE_CREATED",
    "LOCAL_HASH_CREATED",
    "ANCHOR_REQUEST_CREATED",
    "ANCHORING_SIMULATED",
    "ANCHORED",
    "VERIFICATION_EXECUTED",
]

# ── Pipeline steps ──────────────────────────────────────────────────────────
PIPELINE_STEPS = [
    ("upload", "Upload"),
    ("original", "Arquivo Original"),
    ("wrapper", "Wrapper"),
    ("normalization", "Normalização"),
    ("ontology", "Ontologia"),
    ("semantic", "Validação Semântica"),
    ("calculation", "Cálculo"),
    ("approval", "Aprovação"),
    ("publication", "Publicação Final"),
    ("provenance", "Proveniência"),
    ("blockchain", "Blockchain"),
    ("verification", "Verificação"),
]

# ── Dash server ─────────────────────────────────────────────────────────────
DASH_HOST = "127.0.0.1"
DASH_PORT = 8050
DEBUG = True

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
        REPORTS_DIR,
        CYCLES_DIR,
        PROPERTIES_DIR,
        DB_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
