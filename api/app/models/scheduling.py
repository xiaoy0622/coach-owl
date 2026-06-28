"""Recurrence rules and lessons (sessions). Times stored UTC, tz-aware."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, OrgScopedMixin
from app.models._types import str_enum
from app.models.enums import LessonStatus, RecurrenceFreq


class RecurrenceRule(OrgScopedMixin, Base):
    __tablename__ = "recurrence_rules"

    freq: Mapped[RecurrenceFreq] = mapped_column(
        str_enum(RecurrenceFreq, "recurrence_freq"),
        nullable=False,
        default=RecurrenceFreq.weekly,
    )
    interval: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # 0=Monday .. 6=Sunday
    byweekday: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, default=list
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)


class Lesson(OrgScopedMixin, Base):
    __tablename__ = "lessons"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coach_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    recurrence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recurrence_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[LessonStatus] = mapped_column(
        str_enum(LessonStatus, "lesson_status"),
        nullable=False,
        default=LessonStatus.scheduled,
    )
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    credit_deducted: Mapped[bool] = mapped_column(
        default=False, nullable=False
    )
    # Reserved for Phase 2 group classes (1:1 for MVP).
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
