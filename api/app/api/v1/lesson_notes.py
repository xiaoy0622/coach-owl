"""Post-lesson notes router (CO-A02).

Jot/speak after class → AI tidies it into a structured progress note, which the
coach **confirms/edits before it is saved** (§1.4 铁律). The ``/structure`` step
returns a candidate and writes nothing; saving persists the confirmed structure.

    POST   /lesson-notes/structure   raw text → candidate (no save)
    POST   /lesson-notes             save a confirmed note
    GET    /lesson-notes?studentId|lessonId   timeline (org-scoped, newest first)
    GET    /lesson-notes/{id}
    PATCH  /lesson-notes/{id}         re-edit a saved note
    DELETE /lesson-notes/{id}
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentOrg
from app.schemas.common import Page
from app.schemas.lesson_notes import (
    LessonNoteCreate,
    LessonNoteOut,
    LessonNoteUpdate,
    StructuredNote,
    StructureNoteRequest,
)
from app.services import lesson_notes as service

router = APIRouter(prefix="/lesson-notes", tags=["lesson_notes"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/structure", response_model=StructuredNote)
def structure_note(body: StructureNoteRequest, org_id: CurrentOrg):
    # AI candidate only — confirmed/edited before persisting (CO-A02 / §1.4).
    return StructuredNote.model_validate(service.structure_candidate(body.raw_input))


@router.get("", response_model=Page[LessonNoteOut])
def list_notes(
    org_id: CurrentOrg,
    db: DbSession,
    student_id: uuid.UUID | None = None,
    lesson_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
):
    items, next_cursor = service.list_notes(
        db,
        org_id,
        student_id=student_id,
        lesson_id=lesson_id,
        limit=limit,
        cursor=cursor,
    )
    return Page[LessonNoteOut](
        items=[LessonNoteOut.model_validate(n) for n in items],
        next_cursor=next_cursor,
    )


@router.post("", response_model=LessonNoteOut, status_code=201)
def create_note(body: LessonNoteCreate, org_id: CurrentOrg, db: DbSession):
    return LessonNoteOut.model_validate(service.create_note(db, org_id, body))


@router.get("/{note_id}", response_model=LessonNoteOut)
def get_note(note_id: uuid.UUID, org_id: CurrentOrg, db: DbSession):
    return LessonNoteOut.model_validate(service.get_note(db, org_id, note_id))


@router.patch("/{note_id}", response_model=LessonNoteOut)
def update_note(
    note_id: uuid.UUID,
    body: LessonNoteUpdate,
    org_id: CurrentOrg,
    db: DbSession,
):
    return LessonNoteOut.model_validate(
        service.update_note(db, org_id, note_id, body)
    )


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: uuid.UUID, org_id: CurrentOrg, db: DbSession):
    service.delete_note(db, org_id, note_id)
