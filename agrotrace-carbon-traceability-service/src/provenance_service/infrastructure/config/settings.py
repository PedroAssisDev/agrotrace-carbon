"""Runtime settings loaded from environment variables.

All settings are prefixed with ``PROV_`` to avoid conflicts in shared environments.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Loaded from environment variables (prefix ``PROV_``) and ``.env`` files.
    """

    model_config = SettingsConfigDict(
        env_prefix="PROV_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = Field(default="agrotrace-carbon-provenance-service")
    environment: Literal["local", "docker", "test", "staging", "production"] = Field(default="local")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8080, ge=1, le=65535)
    api_root_path: str = Field(default="")

    database_url: str = Field(default="sqlite:///./data/provenance.db")
    database_pool_size: int = Field(default=10, ge=1)
    database_max_overflow: int = Field(default=20, ge=0)
    database_echo: bool = Field(default=False)

    outbox_poll_interval_seconds: float = Field(default=5.0, gt=0.0)
    outbox_batch_size: int = Field(default=100, ge=1, le=10_000)

    hash_default_algorithm: Literal["sha256", "sha3_256"] = Field(default="sha256")

    ontology_client_base_url: str = Field(default="")
    blockchain_client_network: str = Field(default="stub")
    wrapper_metadata_client_base_url: str = Field(default="")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor used as a FastAPI dependency."""
    return Settings()
