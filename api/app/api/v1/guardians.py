"""Guardians router — schemas wired; service is Wave 3 (CO-S02)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.deps import CurrentOrg
from app.core.errors import not_implemented
from app.schemas.common import Page
from app.schemas.guardians import GuardianCreate, GuardianOut, GuardianUpdate

router = APIRouter(prefix="/guardians", tags=["guardians"])


@router.get("", response_model=Page[GuardianOut])
def list_guardians(org_id: CurrentOrg, student_id: uuid.UUID | None = None):
    not_implemented()


@router.post("", response_model=GuardianOut, status_code=201)
def create_guardian(body: GuardianCreate, org_id: CurrentOrg):
    not_implemented()


@router.patch("/{guardian_id}", response_model=GuardianOut)
def update_guardian(guardian_id: uuid.UUID, body: GuardianUpdate, org_id: CurrentOrg):
    not_implemented()
