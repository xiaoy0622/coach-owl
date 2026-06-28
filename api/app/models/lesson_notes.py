"""Post-lesson notes (text/voice -> structured)."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, OrgScopedMixin
from app.models._types import str_enum
from app.models.enums import NoteSource


class LessonNote(OrgScopedMixin, Base):
    __tablename__ = "lesson_notes"

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    # {topics: [...], progress: "...", homework: "..."}
    structured: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    source: Mapped[NoteSource] = mapped_column(
        str_enum(NoteSource, "note_source"),
        nullable=False,
        default=NoteSource.text,
    )
    audio_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
