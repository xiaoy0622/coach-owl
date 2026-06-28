"""Scheduling domain service: recurrence engine + lesson CRUD/conflicts/transitions.

CO-C01 — :func:`expand_recurrence` is a *pure* function turning a
``RecurrenceRule`` into concrete UTC occurrence datetimes. It is DST-correct: each
occurrence's wall-clock ``start_time`` is localized to the org timezone on its own
date, so a "Tuesday 4pm" lesson stays 4pm local across a daylight-saving
transition even though its UTC offset shifts.

CO-C02 — single/recurring lesson creation (recurring expands via the engine),
range listing for week/month calendars, and same-coach time-overlap conflict
detection.

CO-C03 — reschedule / cancel / no_show with a legal status-transition state
machine. Credit deduction and notification emission are intentionally left as
Wave-3 hooks (see the clearly-marked TODOs below) — they depend on the Credits and
Notifications services which are owned by other streams.
"""
from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import scoped
from app.core.errors import AppError
from app.models.enums import LessonStatus
from app.models.organization import Organization
from app.models.scheduling import Lesson, RecurrenceRule
from app.models.student import Student
from app.models.user import User
from app.notifications.dispatcher import notify
from app.notifications.hooks import low_balance_reminder
from app.schemas.scheduling import LessonCreate, LessonUpdate, RecurrenceRuleBase
from app.services import credits as credits_service

logger = logging.getLogger(__name__)

# A hard cap so an open-ended (no ``end_date``) weekly rule can't expand forever.
MAX_OCCURRENCES = 500
_MONDAY = 0  # Python: Monday=0 .. Sunday=6 (matches RecurrenceRule.byweekday).


# --------------------------------------------------------------------------- #
# CO-C01 — Recurrence engine (pure logic)                                      #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Occurrence:
    """A single concrete lesson slot produced by the recurrence engine."""

    starts_at: datetime  # tz-aware UTC
    duration_min: int


def _week_monday(d: date) -> date:
    """The Monday on or before ``d`` (week start = Monday, per iCal default)."""
    return d - timedelta(days=d.weekday())


def expand_recurrence(
    rule: RecurrenceRuleBase | RecurrenceRule,
    tz_name: str,
    *,
    limit: int = MAX_OCCURRENCES,
) -> list[Occurrence]:
    """Expand a weekly recurrence rule into concrete UTC occurrences.

    ``tz_name`` is the org timezone; ``start_time`` is interpreted as *local*
    wall-clock on each occurrence's date and converted to UTC (DST-correct).

    The rule fields used: ``interval`` (every N weeks), ``byweekday`` (0=Mon..
    6=Sun; defaults to the weekday of ``start_date`` when empty), ``start_date``,
    optional ``end_date`` (inclusive), ``start_time`` and ``duration_min``.
    """
    tz = ZoneInfo(tz_name)
    interval = max(1, rule.interval)
    weekdays = sorted(set(rule.byweekday)) or [rule.start_date.weekday()]
    if any(w < 0 or w > 6 for w in weekdays):
        raise AppError(
            "byweekday entries must be 0 (Mon) .. 6 (Sun)",
            code="invalid_recurrence",
        )

    cap = min(limit, MAX_OCCURRENCES)
    anchor_monday = _week_monday(rule.start_date)
    occurrences: list[Occurrence] = []
    week_index = 0
    while True:
        # Only emit on weeks that fall on the interval cadence.
        if week_index % interval == 0:
            base = anchor_monday + timedelta(weeks=week_index)
            for wd in weekdays:
                day = base + timedelta(days=wd)
                if day < rule.start_date:
                    continue
                if rule.end_date is not None and day > rule.end_date:
                    return occurrences
                # Localize the wall-clock time on THIS date, then go to UTC.
                local_dt = datetime.combine(day, rule.start_time, tzinfo=tz)
                occurrences.append(
                    Occurrence(
                        starts_at=local_dt.astimezone(UTC),
                        duration_min=rule.duration_min,
                    )
                )
                if len(occurrences) >= cap:
                    return occurrences
        week_index += 1
        # Open-ended rules stop at the cap; guard against runaway loops.
        if rule.end_date is None and len(occurrences) >= cap:
            return occurrences
        if week_index > cap * interval + 8:  # safety net
            return occurrences


# --------------------------------------------------------------------------- #
# CO-C02/C03 — Lesson persistence, conflicts, transitions                      #
# --------------------------------------------------------------------------- #
def org_timezone(db: Session, org_id: uuid.UUID) -> str:
    org = db.get(Organization, org_id)
    return org.timezone if org else "Australia/Sydney"


def _ensure_utc(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC; normalise aware ones to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _end_of(starts_at: datetime, duration_min: int) -> datetime:
    return starts_at + timedelta(minutes=duration_min)


# Statuses that still occupy the coach's time (cancelled frees the slot).
_BLOCKING_STATUSES = (
    LessonStatus.scheduled,
    LessonStatus.completed,
    LessonStatus.no_show,
)


def find_conflicts(
    db: Session,
    org_id: uuid.UUID,
    coach_id: uuid.UUID,
    starts_at: datetime,
    duration_min: int,
    *,
    exclude_lesson_id: uuid.UUID | None = None,
) -> list[Lesson]:
    """Same-coach, org-scoped lessons whose time overlaps the proposed slot.

    Overlap: ``existing.start < new.end`` AND ``new.start < existing.end``.
    """
    starts_at = _ensure_utc(starts_at)
    new_end = _end_of(starts_at, duration_min)
    stmt = scoped(select(Lesson), org_id, Lesson).where(
        Lesson.coach_id == coach_id,
        Lesson.status.in_(_BLOCKING_STATUSES),
    )
    if exclude_lesson_id is not None:
        stmt = stmt.where(Lesson.id != exclude_lesson_id)
    candidates = db.scalars(stmt).all()
    hits: list[Lesson] = []
    for existing in candidates:
        ex_start = _ensure_utc(existing.starts_at)
        ex_end = _end_of(ex_start, existing.duration_min)
        if ex_start < new_end and starts_at < ex_end:
            hits.append(existing)
    return hits


def _conflict_payload(lessons: Iterable[Lesson]) -> list[dict]:
    return [
        {
            "lessonId": str(lesson.id),
            "coachId": str(lesson.coach_id),
            "startsAt": _ensure_utc(lesson.starts_at).isoformat(),
            "durationMin": lesson.duration_min,
        }
        for lesson in lessons
    ]


def _raise_conflict(lessons: Iterable[Lesson]) -> None:
    raise AppError(
        "Lesson time conflicts with an existing lesson for this coach",
        code="lesson_conflict",
        status_code=409,
        details=_conflict_payload(lessons),
    )


def create_lessons(
    db: Session, org_id: uuid.UUID, body: LessonCreate
) -> list[Lesson]:
    """Create a single lesson, or expand+create a recurring series.

    Raises a 409 ``lesson_conflict`` if any occurrence overlaps an existing
    lesson for the same coach (or another occurrence in the same batch).
    """
    if body.recurrence is not None:
        slots = _recurrence_slots(db, org_id, body)
        recurrence = RecurrenceRule(
            org_id=org_id,
            freq=body.recurrence.freq,
            interval=body.recurrence.interval,
            byweekday=list(body.recurrence.byweekday),
            start_date=body.recurrence.start_date,
            end_date=body.recurrence.end_date,
            start_time=body.recurrence.start_time,
            duration_min=body.recurrence.duration_min,
        )
        db.add(recurrence)
        db.flush()  # assign recurrence.id
        recurrence_id: uuid.UUID | None = recurrence.id
    else:
        slots = [(_ensure_utc(body.starts_at), body.duration_min)]
        recurrence_id = None

    # Conflict check: against the DB and within the batch itself.
    batch: list[tuple[datetime, datetime]] = []
    for starts_at, duration in slots:
        new_end = _end_of(starts_at, duration)
        db_hits = find_conflicts(db, org_id, body.coach_id, starts_at, duration)
        if db_hits:
            _raise_conflict(db_hits)
        for b_start, b_end in batch:
            if b_start < new_end and starts_at < b_end:
                raise AppError(
                    "Recurring occurrences overlap each other",
                    code="lesson_conflict",
                    status_code=409,
                )
        batch.append((starts_at, new_end))

    lessons: list[Lesson] = []
    for starts_at, duration in slots:
        lesson = Lesson(
            org_id=org_id,
            student_id=body.student_id,
            coach_id=body.coach_id,
            recurrence_id=recurrence_id,
            starts_at=starts_at,
            duration_min=duration,
            status=body.status,
            location=body.location,
            meeting_url=body.meeting_url,
        )
        db.add(lesson)
        lessons.append(lesson)
    db.commit()
    for lesson in lessons:
        db.refresh(lesson)
    return lessons


def _recurrence_slots(
    db: Session, org_id: uuid.UUID, body: LessonCreate
) -> list[tuple[datetime, datetime]]:
    tz_name = org_timezone(db, org_id)
    occurrences = expand_recurrence(body.recurrence, tz_name)
    if not occurrences:
        raise AppError(
            "Recurrence rule produced no occurrences",
            code="invalid_recurrence",
        )
    return [(o.starts_at, o.duration_min) for o in occurrences]


def list_lessons(
    db: Session,
    org_id: uuid.UUID,
    from_: datetime | None,
    to: datetime | None,
) -> list[Lesson]:
    """List org lessons overlapping ``[from, to)``, ordered by start time.

    A lesson is included when it overlaps the window (so a lesson that starts
    before ``from`` but runs into it still appears on the week/month view).
    """
    stmt = scoped(select(Lesson), org_id, Lesson).order_by(Lesson.starts_at)
    if to is not None:
        stmt = stmt.where(Lesson.starts_at < _ensure_utc(to))
    rows = db.scalars(stmt).all()
    if from_ is not None:
        from_utc = _ensure_utc(from_)
        rows = [
            lesson
            for lesson in rows
            if _end_of(_ensure_utc(lesson.starts_at), lesson.duration_min)
            > from_utc
        ]
    return list(rows)


def get_lesson(db: Session, org_id: uuid.UUID, lesson_id: uuid.UUID) -> Lesson:
    lesson = db.scalar(
        scoped(select(Lesson), org_id, Lesson).where(Lesson.id == lesson_id)
    )
    if lesson is None:
        raise AppError("Lesson not found", code="not_found", status_code=404)
    return lesson


# Legal status transitions. Terminal states only allow a no-op (same status).
_ALLOWED_TRANSITIONS: dict[LessonStatus, set[LessonStatus]] = {
    LessonStatus.scheduled: {
        LessonStatus.scheduled,
        LessonStatus.completed,
        LessonStatus.cancelled,
        LessonStatus.no_show,
    },
    LessonStatus.completed: {LessonStatus.completed},
    LessonStatus.cancelled: {LessonStatus.cancelled},
    LessonStatus.no_show: {LessonStatus.no_show},
}


def update_lesson(
    db: Session,
    org_id: uuid.UUID,
    lesson_id: uuid.UUID,
    body: LessonUpdate,
) -> Lesson:
    """Reschedule / cancel / mark no_show / complete a lesson.

    Reschedule (changing time/duration) is only permitted while the lesson is
    still ``scheduled`` and re-runs conflict detection. Status changes must be a
    legal transition.
    """
    lesson = get_lesson(db, org_id, lesson_id)

    rescheduling = (
        body.starts_at is not None or body.duration_min is not None
    )
    if rescheduling and lesson.status != LessonStatus.scheduled:
        raise AppError(
            "Only scheduled lessons can be rescheduled",
            code="invalid_transition",
            status_code=409,
        )

    new_starts_at = (
        _ensure_utc(body.starts_at)
        if body.starts_at is not None
        else _ensure_utc(lesson.starts_at)
    )
    new_duration = (
        body.duration_min if body.duration_min is not None else lesson.duration_min
    )
    rescheduled = False
    if rescheduling:
        hits = find_conflicts(
            db,
            org_id,
            lesson.coach_id,
            new_starts_at,
            new_duration,
            exclude_lesson_id=lesson.id,
        )
        if hits:
            _raise_conflict(hits)
        lesson.starts_at = new_starts_at
        lesson.duration_min = new_duration
        rescheduled = True

    status_changed_to: LessonStatus | None = None
    deducted = False
    if body.status is not None and body.status != lesson.status:
        allowed = _ALLOWED_TRANSITIONS[lesson.status]
        if body.status not in allowed:
            raise AppError(
                f"Illegal status transition {lesson.status.value} ->"
                f" {body.status.value}",
                code="invalid_transition",
                status_code=409,
            )
        # Deduction is appended in THIS transaction (no commit) so it lands
        # atomically with the status change below — an insufficient balance
        # rolls the completion back too.
        deducted = _apply_status_change(db, org_id, lesson, body)
        status_changed_to = body.status

    if body.location is not None:
        lesson.location = body.location
    if body.meeting_url is not None:
        lesson.meeting_url = body.meeting_url
    if body.cancel_reason is not None:
        lesson.cancel_reason = body.cancel_reason

    db.commit()
    db.refresh(lesson)

    # Post-commit, channel-agnostic side effects (CO-C03 / CO-K03). These write
    # to the notification outbox and must never break a persisted status change.
    _emit_status_side_effects(
        db,
        org_id,
        lesson,
        status_changed_to=status_changed_to,
        rescheduled=rescheduled,
        deducted=deducted,
    )
    return lesson


def _should_deduct(status: LessonStatus, deduct_credit: bool | None) -> bool:
    """Whether a status transition consumes a credit (CO-C03 policy).

    - ``completed``: deduct by default (§4 invariant 2 — a completed lesson
      burns one credit), unless the request explicitly opts out
      (``deductCredit=false``).
    - ``no_show``: opt-in only — deduct just when ``deductCredit=true``.
    - ``cancelled`` (and a plain reschedule, which never reaches here): no
      deduction. Cancelling frees the slot and refunds nothing/charges nothing.
    """
    if status == LessonStatus.completed:
        return deduct_credit is not False
    if status == LessonStatus.no_show:
        return deduct_credit is True
    return False


def _apply_status_change(
    db: Session, org_id: uuid.UUID, lesson: Lesson, body: LessonUpdate
) -> bool:
    """Apply a status transition and, per policy, deduct a credit.

    Returns ``True`` when a credit was deducted (so the caller knows to check
    for a low-balance reminder after committing). The deduction is appended to
    the immutable ``credit_ledger`` via the Credits service *without* committing
    — it shares this request's transaction so it lands atomically with the
    status change and ``credit_deducted`` (§4 invariant 2). Idempotent: the
    ``credit_deducted`` guard means a lesson can never be double-deducted.
    """
    new_status = body.status
    if new_status in (LessonStatus.cancelled, LessonStatus.no_show):
        if body.cancel_reason is not None:
            lesson.cancel_reason = body.cancel_reason

    lesson.status = new_status

    if lesson.credit_deducted or not _should_deduct(new_status, body.deduct_credit):
        return False

    # Raises ``insufficient_balance`` (409) if the student is out of credit,
    # which rolls back the whole status change (no commit has happened yet).
    credits_service.record_deduction(
        db,
        org_id,
        student_id=lesson.student_id,
        lesson_id=lesson.id,
        count=1,
    )
    lesson.credit_deducted = True
    return True


def _recipient_for(db: Session, lesson: Lesson) -> str | None:
    """Notification recipient: the student's email, falling back to the coach's."""
    student = db.get(Student, lesson.student_id)
    if student is not None and student.email:
        return student.email
    coach = db.get(User, lesson.coach_id)
    if coach is not None and coach.email:
        return coach.email
    return None


def _lesson_payload(lesson: Lesson) -> dict:
    return {
        "lessonId": str(lesson.id),
        "studentId": str(lesson.student_id),
        "coachId": str(lesson.coach_id),
        "startsAt": _ensure_utc(lesson.starts_at).isoformat(),
        "status": lesson.status.value,
    }


def _safe_notify(
    db: Session,
    org_id: uuid.UUID,
    lesson: Lesson,
    *,
    template: str,
    dedupe_key: str,
) -> None:
    """Enqueue an outbox notification, swallowing any failure (never break the
    already-committed status change)."""
    try:
        recipient = _recipient_for(db, lesson)
        if recipient is None:
            return
        notify(
            db,
            org_id=org_id,
            template=template,
            recipient=recipient,
            payload=_lesson_payload(lesson),
            dedupe_key=dedupe_key,
        )
    except Exception:  # noqa: BLE001 — side effect must not surface to caller
        db.rollback()
        logger.exception(
            "Failed to enqueue %s notification for lesson %s", template, lesson.id
        )


def _emit_status_side_effects(
    db: Session,
    org_id: uuid.UUID,
    lesson: Lesson,
    *,
    status_changed_to: LessonStatus | None,
    rescheduled: bool,
    deducted: bool,
) -> None:
    """Fire post-commit linkages: low-balance reminder + cancel/reschedule notice."""
    # CO-K03 — after a deduct, nudge once if the balance fell to/under threshold.
    if deducted:
        try:
            threshold = credits_service.DEFAULT_LOW_BALANCE_THRESHOLD
            balance = credits_service.get_balance(db, org_id, lesson.student_id)
            if balance <= threshold:
                recipient = _recipient_for(db, lesson)
                if recipient is not None:
                    student = db.get(Student, lesson.student_id)
                    low_balance_reminder(
                        db,
                        org_id=org_id,
                        student_id=lesson.student_id,
                        recipient=recipient,
                        balance=balance,
                        threshold=threshold,
                        student_name=student.name if student else None,
                    )
        except Exception:  # noqa: BLE001 — reminder must not break the request
            db.rollback()
            logger.exception(
                "Failed to raise low-balance reminder for lesson %s", lesson.id
            )

    # CO-C03 — a cancellation or reschedule emits a channel-agnostic notice. A
    # cancel wins over a reschedule when both happen in the same PATCH.
    if status_changed_to == LessonStatus.cancelled:
        _safe_notify(
            db,
            org_id,
            lesson,
            template="lesson_cancelled",
            dedupe_key=f"lesson:{lesson.id}:cancelled",
        )
    elif rescheduled:
        # New time in the key so each distinct reschedule notifies once while a
        # replayed PATCH to the same time stays idempotent.
        _safe_notify(
            db,
            org_id,
            lesson,
            template="lesson_rescheduled",
            dedupe_key=(
                f"lesson:{lesson.id}:rescheduled:"
                f"{_ensure_utc(lesson.starts_at).isoformat()}"
            ),
        )
