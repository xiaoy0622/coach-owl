"""Scheduling router — lessons + recurrence (CO-C01/C02/C03).

Times are ISO8601 UTC on the wire; the frontend renders them in the org
timezone. Conflicts return HTTP 409 with ``error.code = "lesson_conflict"`` and a
``details`` list of the overlapping lessons.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentOrg
from app.schemas.common import Page
from app.schemas.scheduling import (
    LessonCreate,
    LessonOut,
    LessonUpdate,
    RecurrencePreviewOut,
    RecurrencePreviewRequest,
)
from app.services import scheduling as service

router = APIRouter(prefix="/lessons", tags=["scheduling"])

DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=Page[LessonOut])
def list_lessons(
    org_id: CurrentOrg,
    db: DbDep,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
):
    """List lessons overlapping ``[from, to)`` for a week/month calendar view."""
    lessons = service.list_lessons(db, org_id, from_, to)
    return Page[LessonOut](
        items=[LessonOut.model_validate(lesson) for lesson in lessons]
    )


@router.post("", response_model=Page[LessonOut], status_code=201)
def create_lesson(body: LessonCreate, org_id: CurrentOrg, db: DbDep):
    """Create a single lesson, or a recurring series expanded via CO-C01."""
    lessons = service.create_lessons(db, org_id, body)
    return Page[LessonOut](
        items=[LessonOut.model_validate(lesson) for lesson in lessons]
    )


@router.post("/recurrence/preview", response_model=RecurrencePreviewOut)
def preview_recurrence(
    body: RecurrencePreviewRequest, org_id: CurrentOrg, db: DbDep
):
    """Preview the concrete (UTC) occurrence times a recurrence would create."""
    tz_name = service.org_timezone(db, org_id)
    occ = service.expand_recurrence(body.recurrence, tz_name, limit=body.limit)
    starts = [o.starts_at for o in occ]
    return RecurrencePreviewOut(occurrences=starts, count=len(starts))


@router.get("/{lesson_id}", response_model=LessonOut)
def get_lesson(lesson_id: uuid.UUID, org_id: CurrentOrg, db: DbDep):
    return LessonOut.model_validate(service.get_lesson(db, org_id, lesson_id))


@router.patch("/{lesson_id}", response_model=LessonOut)
def update_lesson(
    lesson_id: uuid.UUID, body: LessonUpdate, org_id: CurrentOrg, db: DbDep
):
    """Reschedule / cancel / mark no_show / complete a lesson (CO-C03)."""
    lesson = service.update_lesson(db, org_id, lesson_id, body)
    return LessonOut.model_validate(lesson)
