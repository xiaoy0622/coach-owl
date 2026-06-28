"""Students router (CO-S01) — org-scoped CRUD + search + cursor pagination."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentOrg
from app.models.enums import StudentStatus
from app.schemas.common import Page
from app.schemas.students import StudentCreate, StudentOut, StudentUpdate
from app.services import students as service

router = APIRouter(prefix="/students", tags=["students"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=Page[StudentOut])
def list_students(
    org_id: CurrentOrg,
    db: DbSession,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
    search: str | None = None,
    status: StudentStatus | None = None,
    tag: str | None = None,
):
    items, next_cursor = service.list_students(
        db,
        org_id,
        limit=limit,
        cursor=cursor,
        search=search,
        status=status,
        tag=tag,
    )
    return Page[StudentOut](
        items=[StudentOut.model_validate(s) for s in items],
        next_cursor=next_cursor,
    )


@router.post("", response_model=StudentOut, status_code=201)
def create_student(body: StudentCreate, org_id: CurrentOrg, db: DbSession):
    student = service.create_student(db, org_id, body)
    return StudentOut.model_validate(student)


@router.get("/{student_id}", response_model=StudentOut)
def get_student(student_id: uuid.UUID, org_id: CurrentOrg, db: DbSession):
    return StudentOut.model_validate(service.get_student(db, org_id, student_id))


@router.patch("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: uuid.UUID,
    body: StudentUpdate,
    org_id: CurrentOrg,
    db: DbSession,
):
    student = service.update_student(db, org_id, student_id, body)
    return StudentOut.model_validate(student)


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: uuid.UUID, org_id: CurrentOrg, db: DbSession):
    service.delete_student(db, org_id, student_id)
