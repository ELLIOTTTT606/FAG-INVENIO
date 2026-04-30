"""Centralized configuration for INVENIO.

All environment variables are read once at startup, validated with
pydantic-settings, and exposed through `get_settings()` (lru-cached).

Tests can override individual values by clearing the cache and pushing
a custom Settings instance via the `setattr_settings()` context manager
or by setting environment variables before calling `get_settings()`.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = Field(default="development", description="Deployment env name.")
    app_log_level: str = Field(default="INFO")

    baserow_url: str = Field(default="", alias="BASEROW_URL")
    baserow_token: str = Field(default="", alias="BASEROW_TOKEN")
    baserow_timeout_seconds: float = Field(default=10.0, alias="BASEROW_TIMEOUT")
    baserow_max_retries: int = Field(default=3, ge=0, le=10, alias="BASEROW_MAX_RETRIES")
    baserow_cache_ttl_seconds: int = Field(default=300, ge=0, le=3600, alias="BASEROW_CACHE_TTL")

    baserow_table_clients: int = Field(default=0, alias="BASEROW_TABLE_CLIENTS")
    baserow_table_contacts_force_vente: int = Field(
        default=0, alias="BASEROW_TABLE_CONTACTS_FORCE_VENTE"
    )
    baserow_table_contacts_solution: int = Field(
        default=0, alias="BASEROW_TABLE_CONTACTS_SOLUTION"
    )
    baserow_table_options_accessoires: int = Field(
        default=0, alias="BASEROW_TABLE_OPTIONS_ACCESSOIRES"
    )
    baserow_table_designation_decoder: int = Field(
        default=0, alias="BASEROW_TABLE_DESIGNATION_DECODER"
    )

    @property
    def baserow_live(self) -> bool:
        """True when Baserow is fully configured and should be hit live."""

        return bool(self.baserow_url) and bool(self.baserow_token)

    @property
    def baserow_mode(self) -> str:
        return "live" if self.baserow_live else "mock"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    """Re-read environment variables. Useful for tests that monkeypatch env."""

    get_settings.cache_clear()
    return get_settings()


def is_live_baserow_test_enabled() -> bool:
    """True when the test suite is allowed to hit a real Baserow instance."""

    return os.environ.get("INVENIO_BASEROW_LIVE", "").strip().lower() in {"1", "true", "yes"}
