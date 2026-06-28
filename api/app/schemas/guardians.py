"""Guardian contracts (CO-S02)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import CamelModel


class GuardianBase(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    relationship: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    is_primary: bool = False


class GuardianCreate(GuardianBase):
    student_id: uuid.UUID


class GuardianUpdate(CamelModel):
    name: str | None = Field(default=None, max_length=255)
    relationship: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    is_primary: bool | None = None


class GuardianOut(GuardianBase):
    id: uuid.UUID
    org_id: uuid.UUID
    student_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
