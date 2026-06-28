"""Auth + onboarding contracts (CO-F03)."""
from __future__ import annotations

import uuid

from pydantic import EmailStr, Field

from app.models.enums import UserRole
from app.schemas.common import CamelModel
from app.schemas.org import OrgOut


class RegisterRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    org_name: str | None = Field(default=None, max_length=255)


class LoginRequest(CamelModel):
    email: EmailStr
    password: str


class UserOut(CamelModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    role: UserRole
    org_id: uuid.UUID


class AuthResponse(CamelModel):
    """Returned by register/login: token + the authenticated user."""

    token: str
    user: UserOut


class MeResponse(CamelModel):
    """Returned by GET /auth/me."""

    user: UserOut
    org: OrgOut
