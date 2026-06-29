"""v1 API router aggregator."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    compliance,
    credits,
    guardians,
    imports,
    invoices,
    lesson_notes,
    notifications,
    org,
    payments,
    scheduling,
    share_links,
    students,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(org.router)
api_router.include_router(students.router)
api_router.include_router(guardians.router)
api_router.include_router(scheduling.router)
api_router.include_router(credits.router)
api_router.include_router(payments.router)
api_router.include_router(invoices.router)
api_router.include_router(notifications.router)
api_router.include_router(lesson_notes.router)
api_router.include_router(share_links.router)
api_router.include_router(imports.router)
api_router.include_router(compliance.router)
