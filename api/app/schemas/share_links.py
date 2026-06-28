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
