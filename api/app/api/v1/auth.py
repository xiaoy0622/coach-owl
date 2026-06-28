"""Auth + onboarding endpoints (CO-F03)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.deps import CurrentPrincipal
from app.core.errors import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    UserOut,
)
from app.schemas.org import OrgOut

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        org_id=user.org_id,
    )


def _issue(user: User) -> AuthResponse:
    token = create_access_token(
        user_id=str(user.id), org_id=str(user.org_id), role=user.role.value
    )
    return AuthResponse(token=token, user=_user_out(user))


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
def register(body: RegisterRequest, db: DbSession) -> AuthResponse:
    existing = db.scalar(select(User).where(User.email == body.email.lower()))
    if existing is not None:
        raise AppError(
            "Email already registered",
            code="email_taken",
            status_code=status.HTTP_409_CONFLICT,
        )

    org = Organization(
        name=body.org_name or f"{body.name}'s Studio",
        timezone=settings.default_timezone,
        currency=settings.default_currency,
        gst_enabled=False,
        gst_rate=settings.default_gst_rate,
    )
    db.add(org)
    db.flush()  # assign org.id

    user = User(
        org_id=org.id,
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        name=body.name,
        role=UserRole.owner,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue(user)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: DbSession) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError(
            "Invalid email or password",
            code="invalid_credentials",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    if not user.is_active:
        raise AppError(
            "Account is inactive",
            code="inactive",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return _issue(user)


@router.get("/me", response_model=MeResponse)
def me(principal: CurrentPrincipal, db: DbSession) -> MeResponse:
    org = db.get(Organization, principal.org_id)
    if org is None:
        raise AppError("Org not found", code="not_found", status_code=404)
    return MeResponse(
        user=_user_out(principal.user),
        org=OrgOut.model_validate(org),
    )
