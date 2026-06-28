"""Lesson note contracts (CO-A02)."""
from __future__ import annotations

import uuid
from datetime import datetime

from app.models.enums import NoteSource
from app.schemas.common import CamelModel


class StructuredNote(CamelModel):
    topics: list[str] = []
    progress: str | None = None
    homework: str | None = None


class LessonNoteCreate(CamelModel):
    lesson_id: uuid.UUID
    student_id: uuid.UUID
    raw_input: str | None = None
    structured: StructuredNote = StructuredNote()
    source: NoteSource = NoteSource.text
    audio_url: str | None = None


class LessonNoteUpdate(CamelModel):
    """Patch a saved note (re-edit the confirmed structure / raw jot)."""

    raw_input: str | None = None
    structured: StructuredNote | None = None
    source: NoteSource | None = None
    audio_url: str | None = None


class LessonNoteOut(CamelModel):
    id: uuid.UUID
    org_id: uuid.UUID
    lesson_id: uuid.UUID
    student_id: uuid.UUID
    raw_input: str | None = None
    structured: dict
    source: NoteSource
    audio_url: str | None = None
    created_at: datetime


class StructureNoteRequest(CamelModel):
    """AI: raw text -> candidate structured note (confirmed before persist)."""

    raw_input: str
