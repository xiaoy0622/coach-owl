"""Student contracts (CO-S01)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.models.enums import StudentStatus
from app.schemas.common import CamelModel


class StudentBase(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    status: StudentStatus = StudentStatus.active
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class StudentCreate(StudentBase):
    pass


class StudentUpdate(CamelModel):
    name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    status: StudentStatus | None = None
    tags: list[str] | None = None
    notes: str | None = None


class StudentOut(StudentBase):
    id: uuid.UUID
    org_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
