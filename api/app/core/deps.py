"""Auth + tenancy dependencies.

``current_user`` decodes the Bearer JWT and loads the active user; ``current_org``
exposes the caller's org id. ``scoped(stmt)`` is the org-scoping helper every
data query must pass through — it appends ``WHERE org_id = :current_org`` so a
caller can never read another tenant's rows.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.models.enums import UserRole
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    """The authenticated caller: the user row + their org id (from the JWT)."""

    user: User
    org_id: uuid.UUID

    @property
    def role(self) -> UserRole:
        return self.user.role


def get_current_principal(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> Principal:
    if creds is None or not creds.credentials:
        raise AppError(
            "Missing bearer token", code="unauthorized", status_code=401
        )
    try:
        claims = decode_access_token(creds.credentials)
    except jwt.PyJWTError as exc:
        raise AppError(
            "Invalid or expired token", code="unauthorized", status_code=401
        ) from exc

    user_id = claims.get("sub")
    org_id = claims.get("org_id")
    if not user_id or not org_id:
        raise AppError("Malformed token", code="unauthorized", status_code=401)

    user = db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise AppError(
            "User not found or inactive", code="unauthorized", status_code=401
        )
    # The token's org must match the user's org (defence in depth).
    if str(user.org_id) != str(org_id):
        raise AppError("Token/org mismatch", code="forbidden", status_code=403)

    return Principal(user=user, org_id=user.org_id)


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


def current_user(principal: CurrentPrincipal) -> User:
    return principal.user


def current_org(principal: CurrentPrincipal) -> uuid.UUID:
    return principal.org_id


CurrentUser = Annotated[User, Depends(current_user)]
CurrentOrg = Annotated[uuid.UUID, Depends(current_org)]


def require_owner(principal: CurrentPrincipal) -> Principal:
    if principal.role != UserRole.owner:
        raise AppError(
            "Owner role required", code="forbidden", status_code=403
        )
    return principal


RequireOwner = Annotated[Principal, Depends(require_owner)]


def scoped(stmt: Select, org_id: uuid.UUID, model) -> Select:
    """Append the mandatory ``org_id`` filter to a SELECT (tenant isolation)."""
    return stmt.where(model.org_id == org_id)
