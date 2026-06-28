"""Students router — schemas wired; service is Wave 2 (CO-S01)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.deps import CurrentOrg
from app.core.errors import not_implemented
from app.schemas.common import Page
from app.schemas.students import StudentCreate, StudentOut, StudentUpdate

router = APIRouter(prefix="/students", tags=["students"])


@router.get("", response_model=Page[StudentOut])
def list_students(org_id: CurrentOrg, limit: int = 50, cursor: str | None = None):
    not_implemented()


@router.post("", response_model=StudentOut, status_code=201)
def create_student(body: StudentCreate, org_id: CurrentOrg):
    not_implemented()


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: uuid.UUID, org_id: CurrentOrg):
    not_implemented()


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(student_id: uuid.UUID, body: StudentUpdate, org_id: CurrentOrg):
    not_implemented()


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: uuid.UUID, org_id: CurrentOrg):
    not_implemented()
