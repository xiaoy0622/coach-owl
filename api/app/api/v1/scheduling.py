"""Scheduling router — lessons; service is Wave 2/3 (CO-C02/C03)."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter

from app.core.deps import CurrentOrg
from app.core.errors import not_implemented
from app.schemas.common import Page
from app.schemas.scheduling import LessonCreate, LessonOut, LessonUpdate

router = APIRouter(prefix="/lessons", tags=["scheduling"])


@router.get("", response_model=Page[LessonOut])
def list_lessons(
    org_id: CurrentOrg,
    from_: datetime | None = None,
    to: datetime | None = None,
):
    not_implemented()


@router.post("", response_model=Page[LessonOut], status_code=201)
def create_lesson(body: LessonCreate, org_id: CurrentOrg):
    # May expand a recurrence into multiple occurrences (CO-C01).
    not_implemented()


@router.get("/{lesson_id}", response_model=LessonOut)
def get_lesson(lesson_id: uuid.UUID, org_id: CurrentOrg):
    not_implemented()


@router.patch("/{lesson_id}", response_model=LessonOut)
def update_lesson(lesson_id: uuid.UUID, body: LessonUpdate, org_id: CurrentOrg):
    # Reschedule / cancel / no_show (+ optional credit deduction).
    not_implemented()
