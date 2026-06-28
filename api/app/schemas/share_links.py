"""Share link contracts (CO-W06)."""
from __future__ import annotations

import uuid
from datetime import datetime

from app.schemas.common import CamelModel


class ShareLinkCreate(CamelModel):
    student_id: uuid.UUID
    expires_at: datetime | None = None


class ShareLinkOut(CamelModel):
    id: uuid.UUID
    org_id: uuid.UUID
    student_id: uuid.UUID
    token: str
    expires_at: datetime | None = None
    created_at: datetime


class PublicLessonOut(CamelModel):
    """One upcoming lesson on the public (no-login) share page."""

    starts_at: datetime  # ISO8601 UTC; rendered in the org timezone
    duration_min: int
    location: str | None = None
    meeting_url: str | None = None


class PublicShareOut(CamelModel):
    """Everything a public share token exposes — one student, nothing more."""

    student_name: str
    timezone: str  # org timezone the page renders times in
    credit_balance: int
    upcoming_lessons: list[PublicLessonOut]
