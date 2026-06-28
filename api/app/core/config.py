"""Application settings, loaded from environment / .env (pydantic-settings)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    app_name: str = "CoachOwl API"
    environment: str = "development"
    debug: bool = True

    # Database
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5434/coachowl"
    )

    # Auth / JWT
    jwt_secret: str = "dev-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7  # 7 days

    # Infra
    redis_url: str = "redis://localhost:6380/0"

    # Org defaults (AU localization)
    default_timezone: str = "Australia/Sydney"
    default_currency: str = "AUD"
    default_gst_rate: str = "0.10"

    # AI (optional; not used by foundation)
    anthropic_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
