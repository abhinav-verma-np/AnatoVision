"""
Centralized application settings.

Reads from environment variables (and a local .env file in development via
pydantic-settings). Phase 1 only *plumbs* DATABASE_URL and REDIS_URL through
so the wiring exists end-to-end — no DB/Redis client is opened yet, since no
feature in this phase needs persistence. That connection work belongs to
whichever future phase first needs it (e.g. Bookmarks sync, Quiz progress).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AnatoVision API"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development", alias="APP_ENV")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    # Comma-separated list of allowed browser origins for CORS. Required in
    # addition to the constitution's baseline env vars because without it,
    # the frontend's connection test (requirement #4) would fail purely on
    # a CORS rejection, not a real backend-down state.
    cors_origins: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so Settings() is only constructed once per process."""
    return Settings()
