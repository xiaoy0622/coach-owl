"""Lesson notes router — text/voice -> structured; service is Wave 3 (CO-A02)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.deps import CurrentOrg
from app.core.errors import not_implemented
from app.schemas.common import Page
from app.schemas.lesson_notes import (
    LessonNoteCreate,
    LessonNoteOut,
    StructuredNote,
    StructureNoteRequest,
)

router = APIRouter(prefix="/lesson-notes", tags=["lesson_notes"])


@router.get("", response_model=Page[LessonNoteOut])
def list_notes(org_id: CurrentOrg, student_id: uuid.UUID | None = None):
    not_implemented()


@router.post("", response_model=LessonNoteOut, status_code=201)
def create_note(body: LessonNoteCreate, org_id: CurrentOrg):
    not_implemented()


@router.post("/structure", response_model=StructuredNote)
def structure_note(body: StructureNoteRequest, org_id: CurrentOrg):
    # AI candidate; confirmed/edited before persisting (CO-A02).
    not_implemented()
