from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BLOCKCHAIN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(default=f"sqlite:///{ROOT_DIR / 'data' / 'blockchain_service.db'}")
    provenance_database_url: str = Field(
        default=str(
            ROOT_DIR.parent / "agrotrace-carbon-traceability-service" / "data" / "provenance.db"
        )
    )
    environment: str = Field(default="local")
    service_name: str = Field(default="agrotrace-carbon-blockchain-service")
    observer_batch_size: int = Field(default=100)
    default_network_code: str = Field(default="local_simulated")
    canonicalization_method: str = Field(default="json_canonical_v1")
    hash_algorithm: str = Field(default="sha256")


@lru_cache
def get_settings() -> Settings:
    return Settings()
