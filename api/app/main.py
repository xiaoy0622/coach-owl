"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI

# Importing the models package registers every table on Base.metadata.
import app.models  # noqa: F401,E402
from app.api.v1 import api_router
from app.core.config import settings
from app.core.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="CoachOwl — lightweight tutor/coach management SaaS (AU).",
    )

    register_error_handlers(app)

    @app.get("/api/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(api_router)
    return app


app = create_app()
