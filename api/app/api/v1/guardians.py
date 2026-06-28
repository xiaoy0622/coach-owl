"""Guardians router (CO-S02) — multiple guardians per student, is_primary,
minor students must keep a primary guardian (enforced in the service)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentOrg
from app.schemas.common import Page
from app.schemas.guardians import GuardianCreate, GuardianOut, GuardianUpdate
from app.services import guardians as service

router = APIRouter(prefix="/guardians", tags=["guardians"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=Page[GuardianOut])
def list_guardians(
    org_id: CurrentOrg,
    db: DbSession,
    student_id: uuid.UUID | None = None,
):
    items = service.list_guardians(db, org_id, student_id)
    return Page[GuardianOut](
        items=[GuardianOut.model_validate(g) for g in items], next_cursor=None
    )


@router.post("", response_model=GuardianOut, status_code=201)
def create_guardian(body: GuardianCreate, org_id: CurrentOrg, db: DbSession):
    return GuardianOut.model_validate(service.create_guardian(db, org_id, body))


@router.patch("/{guardian_id}", response_model=GuardianOut)
def update_guardian(
    guardian_id: uuid.UUID,
    body: GuardianUpdate,
    org_id: CurrentOrg,
    db: DbSession,
):
    guardian = service.update_guardian(db, org_id, guardian_id, body)
    return GuardianOut.model_validate(guardian)


@router.delete("/{guardian_id}", status_code=204)
def delete_guardian(guardian_id: uuid.UUID, org_id: CurrentOrg, db: DbSession):
    service.delete_guardian(db, org_id, guardian_id)
