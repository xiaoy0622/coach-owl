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

    # AI (optional). When ``anthropic_api_key`` is unset every AI path degrades
    # to a deterministic, network-free heuristic — so tests / CI run offline.
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_timeout: float = 8.0
    anthropic_max_tokens: int = 1024

    # Email delivery (CO-N02). ``email_provider`` selects the email adapter the
    # registry installs: ``console`` (default — logs only, no key, used by tests
    # and local dev) or ``resend`` (real REST send). A future ``ses`` value slots
    # in the same way. When provider=resend but ``resend_api_key`` is unset, the
    # adapter degrades to a logged ``SendResult.failure`` (never crashes the
    # worker) — keep the default ``console`` so nothing offline needs a key.
    email_provider: str = "console"
    resend_api_key: str | None = None
    email_from: str = "CoachOwl <noreply@coachowl.example>"
    resend_base_url: str = "https://api.resend.com"
    resend_timeout: float = 8.0


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
