"""Scheduling contracts: recurrence rules + lessons (CO-C01/C02/C03)."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import Field

from app.models.enums import LessonStatus, RecurrenceFreq
from app.schemas.common import CamelModel


class RecurrenceRuleBase(CamelModel):
    freq: RecurrenceFreq = RecurrenceFreq.weekly
    interval: int = Field(default=1, ge=1)
    byweekday: list[int] = Field(default_factory=list)  # 0=Mon..6=Sun
    start_date: date
    end_date: date | None = None
    start_time: time
    duration_min: int = Field(gt=0)


class RecurrenceRuleCreate(RecurrenceRuleBase):
    pass


class RecurrenceRuleOut(RecurrenceRuleBase):
    id: uuid.UUID
    org_id: uuid.UUID


class LessonBase(CamelModel):
    student_id: uuid.UUID
    coach_id: uuid.UUID
    starts_at: datetime
    duration_min: int = Field(gt=0)
    status: LessonStatus = LessonStatus.scheduled
    location: str | None = Field(default=None, max_length=255)
    meeting_url: str | None = Field(default=None, max_length=512)


class LessonCreate(LessonBase):
    recurrence: RecurrenceRuleCreate | None = None


class LessonUpdate(CamelModel):
    starts_at: datetime | None = None
    duration_min: int | None = Field(default=None, gt=0)
    status: LessonStatus | None = None
    location: str | None = Field(default=None, max_length=255)
    meeting_url: str | None = Field(default=None, max_length=512)
    cancel_reason: str | None = None
    deduct_credit: bool | None = None


class LessonOut(LessonBase):
    id: uuid.UUID
    org_id: uuid.UUID
    recurrence_id: uuid.UUID | None = None
    cancel_reason: str | None = None
    credit_deducted: bool
    capacity: int
    created_at: datetime
    updated_at: datetime


class LessonConflict(CamelModel):
    """One existing lesson that overlaps a proposed time (same coach)."""

    lesson_id: uuid.UUID
    coach_id: uuid.UUID
    starts_at: datetime
    duration_min: int


class RecurrencePreviewRequest(CamelModel):
    """Expand a recurrence rule into concrete occurrence start times (UTC)."""

    recurrence: RecurrenceRuleCreate
    limit: int = Field(default=100, ge=1, le=500)


class RecurrencePreviewOut(CamelModel):
    occurrences: list[datetime]  # ISO8601 UTC, tz-aware
    count: int
