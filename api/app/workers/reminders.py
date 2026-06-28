"""Pre-lesson reminder scan (CO-N04).

:func:`scan_due_reminders` is a plain, testable function: given "now" it returns
the reminders that have just become due across all orgs (this is a system worker,
not a user request, so it intentionally scans every tenant — each candidate
carries its own ``org_id`` for the dispatcher). :func:`enqueue_reminders` feeds
those candidates through :func:`notify`, whose ``dedupe_key`` guarantee makes the
whole thing idempotent: re-running the scan never double-sends a reminder.

A reminder for offset *X* (e.g. 24h, 1h before start) fires the first scan after
``now`` crosses ``starts_at - X`` while the lesson is still in the future. The
``dedupe_key`` is ``lesson:{id}:reminder:{label}`` so each offset fires exactly
once per lesson.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import LessonStatus, NotificationChannel
from app.models.notifications import Notification
from app.models.scheduling import Lesson
from app.models.student import Student
from app.models.user import User
from app.notifications.dispatcher import notify


@dataclass(frozen=True)
class ReminderOffset:
    """A lead time before a lesson at which to remind (label used in dedupe)."""

    label: str
    delta: timedelta


# Configured offsets (most-distant first). Swap/extend without touching callers.
DEFAULT_OFFSETS: tuple[ReminderOffset, ...] = (
    ReminderOffset("24h", timedelta(hours=24)),
    ReminderOffset("1h", timedelta(hours=1)),
)


@dataclass(frozen=True)
class ReminderCandidate:
    """A single (lesson, offset) reminder that is due to be enqueued."""

    lesson_id: uuid.UUID
    org_id: uuid.UUID
    offset: ReminderOffset
    recipient: str
    starts_at: datetime
    student_name: str

    @property
    def dedupe_key(self) -> str:
        return f"lesson:{self.lesson_id}:reminder:{self.offset.label}"

    @property
    def payload(self) -> dict:
        return {
            "lessonId": str(self.lesson_id),
            "studentName": self.student_name,
            "startsAt": self.starts_at.isoformat(),
            "offset": self.offset.label,
        }


def _resolve_recipient(student: Student, coach: User) -> str:
    """Who gets the reminder: the student, falling back to their coach."""
    return student.email or coach.email


def scan_due_reminders(
    db: Session,
    *,
    now: datetime | None = None,
    offsets: tuple[ReminderOffset, ...] = DEFAULT_OFFSETS,
) -> list[ReminderCandidate]:
    """Return reminders that are due as of ``now`` (default: utcnow).

    A lesson contributes a candidate for every offset whose threshold
    (``starts_at - offset``) is at or before ``now`` while the lesson has not yet
    started. Only ``scheduled`` lessons are considered.
    """
    now = now or datetime.now(UTC)
    if not offsets:
        return []
    max_delta = max(o.delta for o in offsets)

    rows = db.execute(
        select(Lesson, Student, User)
        .join(Student, Student.id == Lesson.student_id)
        .join(User, User.id == Lesson.coach_id)
        .where(Lesson.status == LessonStatus.scheduled)
        .where(Lesson.starts_at > now)
        .where(Lesson.starts_at <= now + max_delta)
        .order_by(Lesson.starts_at.asc())
    ).all()

    candidates: list[ReminderCandidate] = []
    for lesson, student, coach in rows:
        starts_at = lesson.starts_at
        for offset in offsets:
            # Threshold crossed (starts_at - delta <= now) and still upcoming.
            if starts_at - offset.delta <= now:
                candidates.append(
                    ReminderCandidate(
                        lesson_id=lesson.id,
                        org_id=lesson.org_id,
                        offset=offset,
                        recipient=_resolve_recipient(student, coach),
                        starts_at=starts_at,
                        student_name=student.name,
                    )
                )
    return candidates


def enqueue_reminders(
    db: Session,
    *,
    now: datetime | None = None,
    offsets: tuple[ReminderOffset, ...] = DEFAULT_OFFSETS,
) -> list[Notification]:
    """Scan + enqueue due reminders. Idempotent via per-offset dedupe keys."""
    candidates = scan_due_reminders(db, now=now, offsets=offsets)
    return [
        notify(
            db,
            org_id=c.org_id,
            channel=NotificationChannel.email,
            template="lesson_reminder",
            recipient=c.recipient,
            payload=c.payload,
            dedupe_key=c.dedupe_key,
        )
        for c in candidates
    ]
