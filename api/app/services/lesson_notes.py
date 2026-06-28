"""Post-lesson notes service (CO-A02).

Two responsibilities, kept apart so AI output is never silently written
(§1.4 铁律):

1. ``structure_candidate`` — runs the AI structurer over raw text and returns a
   CANDIDATE ``{topics, progress, homework}``. It does **not** touch the database.
2. CRUD — ``create_note`` persists the user-confirmed/edited structure; the rest
   read / update / delete. Every query is org-scoped via ``scoped(...)`` so a
   caller can never reach another tenant's notes, and ``create_note`` verifies the
   referenced lesson belongs to the caller's org before writing.

Listing is a per-student/lesson timeline ordered newest-first with keyset
(cursor) pagination on ``(created_at, id)``.
"""
from __future__ import annotations

import base64
import binascii
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.note_structurer import structure_note
from app.core.deps import scoped
from app.core.errors import AppError
from app.models.lesson_notes import LessonNote
from app.models.scheduling import Lesson
from app.schemas.lesson_notes import LessonNoteCreate, LessonNoteUpdate

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


# --------------------------------------------------------------------------- #
# AI candidate (no persistence)
# --------------------------------------------------------------------------- #
def structure_candidate(raw_input: str) -> dict:
    """AI structuring of raw text → candidate. Never persists (CO-A02)."""
    return structure_note(raw_input)


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #
def create_note(
    db: Session, org_id: uuid.UUID, data: LessonNoteCreate
) -> LessonNote:
    # The lesson must belong to this org; derive/validate the student from it so
    # a note can't be attached across tenants or to a mismatched student.
    lesson = db.scalar(
        scoped(select(Lesson), org_id, Lesson).where(Lesson.id == data.lesson_id)
    )
    if lesson is None:
        raise AppError("Lesson not found", code="not_found", status_code=404)
    if lesson.student_id != data.student_id:
        raise AppError(
            "studentId does not match the lesson's student",
            code="student_mismatch",
            status_code=422,
        )

    note = LessonNote(
        org_id=org_id,
        lesson_id=data.lesson_id,
        student_id=data.student_id,
        raw_input=data.raw_input,
        structured=data.structured.model_dump(),
        source=data.source,
        audio_url=data.audio_url,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_note(
    db: Session, org_id: uuid.UUID, note_id: uuid.UUID
) -> LessonNote:
    note = db.scalar(
        scoped(select(LessonNote), org_id, LessonNote).where(
            LessonNote.id == note_id
        )
    )
    if note is None:
        raise AppError("Note not found", code="not_found", status_code=404)
    return note


def list_notes(
    db: Session,
    org_id: uuid.UUID,
    *,
    student_id: uuid.UUID | None = None,
    lesson_id: uuid.UUID | None = None,
    limit: int = _DEFAULT_LIMIT,
    cursor: str | None = None,
) -> tuple[list[LessonNote], str | None]:
    limit = max(1, min(limit, _MAX_LIMIT))

    stmt = scoped(select(LessonNote), org_id, LessonNote)
    if student_id is not None:
        stmt = stmt.where(LessonNote.student_id == student_id)
    if lesson_id is not None:
        stmt = stmt.where(LessonNote.lesson_id == lesson_id)

    # Newest-first timeline; keyset is strictly *before* the last seen row.
    stmt = stmt.order_by(LessonNote.created_at.desc(), LessonNote.id.desc())
    if cursor:
        c_created, c_id = _decode_cursor(cursor)
        stmt = stmt.where(
            (LessonNote.created_at, LessonNote.id) < (c_created, c_id)
        )

    rows = db.scalars(stmt.limit(limit + 1)).all()
    has_more = len(rows) > limit
    items = list(rows[:limit])
    next_cursor = _encode_cursor(items[-1]) if has_more and items else None
    return items, next_cursor


def update_note(
    db: Session,
    org_id: uuid.UUID,
    note_id: uuid.UUID,
    data: LessonNoteUpdate,
) -> LessonNote:
    note = get_note(db, org_id, note_id)
    fields = data.model_dump(exclude_unset=True)

    if "raw_input" in fields:
        note.raw_input = data.raw_input
    if "structured" in fields and data.structured is not None:
        note.structured = data.structured.model_dump()
    if "source" in fields and data.source is not None:
        note.source = data.source
    if "audio_url" in fields:
        note.audio_url = data.audio_url

    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, org_id: uuid.UUID, note_id: uuid.UUID) -> None:
    note = get_note(db, org_id, note_id)
    db.delete(note)
    db.commit()


# --------------------------------------------------------------------------- #
# Cursor helpers (keyset on created_at|id)
# --------------------------------------------------------------------------- #
def _encode_cursor(item: LessonNote) -> str:
    raw = f"{item.created_at.isoformat()}|{item.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_raw, id_raw = raw.split("|", 1)
        return datetime.fromisoformat(created_raw), uuid.UUID(id_raw)
    except (ValueError, binascii.Error) as exc:
        raise AppError(
            "Invalid pagination cursor",
            code="invalid_cursor",
            status_code=400,
        ) from exc
