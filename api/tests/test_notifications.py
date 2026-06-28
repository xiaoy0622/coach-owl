"""Notifications layer (CO-N01/N04): dispatcher dedupe, console adapter, outbox
processor (no double-send), reminder scan + idempotent keys, low-balance hook,
and the org-scoped router.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.models.enums import (
    LessonStatus,
    NotificationStatus,
    UserRole,
)
from app.models.notifications import Notification
from app.models.organization import Organization
from app.models.scheduling import Lesson
from app.models.student import Student
from app.models.user import User
from app.notifications.adapters import ConsoleEmailAdapter, default_registry
from app.notifications.adapters.registry import AdapterRegistry
from app.notifications.dispatcher import notify
from app.notifications.hooks import low_balance_reminder
from app.notifications.processor import process_outbox
from app.workers.reminders import (
    DEFAULT_OFFSETS,
    enqueue_reminders,
    scan_due_reminders,
)

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


# --------------------------------------------------------------------------- #
# Fixtures-as-helpers (direct ORM inserts; the worker scans across orgs).      #
# --------------------------------------------------------------------------- #
def _org(db, name="Acme Tutoring") -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _coach(db, org_id, email="coach@example.com") -> User:
    user = User(
        org_id=org_id,
        email=email,
        password_hash="x",
        name="Coach",
        role=UserRole.owner,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _student(db, org_id, *, email="sam@example.com", name="Sam") -> Student:
    student = Student(org_id=org_id, name=name, email=email)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def _lesson(
    db, org_id, student_id, coach_id, starts_at, *, status=LessonStatus.scheduled
) -> Lesson:
    lesson = Lesson(
        org_id=org_id,
        student_id=student_id,
        coach_id=coach_id,
        starts_at=starts_at,
        duration_min=60,
        status=status,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def _count(db, **where) -> int:
    stmt = select(func.count()).select_from(Notification)
    for col, val in where.items():
        stmt = stmt.where(getattr(Notification, col) == val)
    return db.scalar(stmt)


# --------------------------------------------------------------------------- #
# Dispatcher idempotency (§4 invariant 3)                                      #
# --------------------------------------------------------------------------- #
def test_notify_dedupes_on_key(db):
    org = _org(db)
    first = notify(
        db,
        org_id=org.id,
        template="lesson_reminder",
        recipient="a@example.com",
        dedupe_key="k-dupe",
    )
    second = notify(
        db,
        org_id=org.id,
        template="lesson_reminder",
        recipient="a@example.com",
        dedupe_key="k-dupe",
    )
    assert first.id == second.id
    assert first.status == NotificationStatus.pending
    assert _count(db, dedupe_key="k-dupe") == 1


# --------------------------------------------------------------------------- #
# Console adapter + outbox processor                                           #
# --------------------------------------------------------------------------- #
def test_console_adapter_returns_success(db):
    org = _org(db)
    note = notify(
        db,
        org_id=org.id,
        template="t",
        recipient="a@example.com",
        dedupe_key="k-adapter",
    )
    result = ConsoleEmailAdapter().send(note)
    assert result.ok is True
    assert result.error is None


def test_process_outbox_marks_sent(db):
    org = _org(db)
    notify(
        db,
        org_id=org.id,
        template="t",
        recipient="a@example.com",
        dedupe_key="k-send",
    )
    result = process_outbox(db, now=NOW)
    assert (result.processed, result.sent, result.failed) == (1, 1, 0)

    note = db.scalar(
        select(Notification).where(Notification.dedupe_key == "k-send")
    )
    assert note.status == NotificationStatus.sent
    assert note.sent_at is not None
    assert note.error is None


def test_process_outbox_does_not_double_send(db):
    org = _org(db)
    notify(
        db,
        org_id=org.id,
        template="t",
        recipient="a@example.com",
        dedupe_key="k-once",
    )
    first = process_outbox(db, now=NOW)
    assert first.sent == 1
    sent_at = db.scalar(
        select(Notification.sent_at).where(Notification.dedupe_key == "k-once")
    )

    # Re-running picks up nothing — already-sent rows are never reconsidered.
    second = process_outbox(db, now=NOW + timedelta(minutes=5))
    assert (second.processed, second.sent, second.failed) == (0, 0, 0)
    still = db.scalar(
        select(Notification.sent_at).where(Notification.dedupe_key == "k-once")
    )
    assert still == sent_at


def test_process_outbox_respects_scheduled_for(db):
    org = _org(db)
    notify(
        db,
        org_id=org.id,
        template="t",
        recipient="a@example.com",
        dedupe_key="k-future",
        scheduled_for=NOW + timedelta(hours=2),
    )
    # Not yet due.
    assert process_outbox(db, now=NOW).processed == 0
    note = db.scalar(
        select(Notification).where(Notification.dedupe_key == "k-future")
    )
    assert note.status == NotificationStatus.pending

    # Due now.
    assert process_outbox(db, now=NOW + timedelta(hours=3)).sent == 1
    db.refresh(note)
    assert note.status == NotificationStatus.sent


def test_process_outbox_marks_failed_when_no_adapter(db):
    org = _org(db)
    notify(
        db,
        org_id=org.id,
        template="t",
        recipient="a@example.com",
        dedupe_key="k-fail",
    )
    empty = AdapterRegistry()  # no email adapter registered
    result = process_outbox(db, registry=empty, now=NOW)
    assert (result.sent, result.failed) == (0, 1)
    note = db.scalar(
        select(Notification).where(Notification.dedupe_key == "k-fail")
    )
    assert note.status == NotificationStatus.failed
    assert note.error


# --------------------------------------------------------------------------- #
# Reminder scan (CO-N04)                                                       #
# --------------------------------------------------------------------------- #
def test_scan_selects_due_offsets_only(db):
    org = _org(db)
    coach = _coach(db, org.id)
    student = _student(db, org.id)

    soon = _lesson(
        db, org.id, student.id, coach.id, NOW + timedelta(minutes=30)
    )  # 24h + 1h both crossed
    mid = _lesson(
        db, org.id, student.id, coach.id, NOW + timedelta(hours=5)
    )  # only 24h crossed
    # Beyond the largest offset -> nothing due yet.
    _lesson(db, org.id, student.id, coach.id, NOW + timedelta(hours=30))
    # Already started -> excluded.
    _lesson(db, org.id, student.id, coach.id, NOW - timedelta(hours=1))
    # Cancelled but soon -> excluded by status.
    _lesson(
        db,
        org.id,
        student.id,
        coach.id,
        NOW + timedelta(minutes=20),
        status=LessonStatus.cancelled,
    )

    candidates = scan_due_reminders(db, now=NOW)
    got = {(c.lesson_id, c.offset.label) for c in candidates}
    assert got == {
        (soon.id, "24h"),
        (soon.id, "1h"),
        (mid.id, "24h"),
    }
    # Dedupe keys follow the documented convention.
    keys = {c.dedupe_key for c in candidates}
    assert f"lesson:{soon.id}:reminder:1h" in keys
    assert f"lesson:{mid.id}:reminder:24h" in keys


def test_scan_recipient_falls_back_to_coach(db):
    org = _org(db)
    coach = _coach(db, org.id, email="thecoach@example.com")
    student = _student(db, org.id, email=None)
    _lesson(db, org.id, student.id, coach.id, NOW + timedelta(minutes=30))

    candidates = scan_due_reminders(db, now=NOW, offsets=DEFAULT_OFFSETS[:1])
    assert len(candidates) == 1
    assert candidates[0].recipient == "thecoach@example.com"


def test_enqueue_reminders_is_idempotent(db):
    org = _org(db)
    coach = _coach(db, org.id)
    student = _student(db, org.id)
    lesson = _lesson(db, org.id, student.id, coach.id, NOW + timedelta(minutes=30))

    first = enqueue_reminders(db, now=NOW)
    assert {n.dedupe_key for n in first} == {
        f"lesson:{lesson.id}:reminder:24h",
        f"lesson:{lesson.id}:reminder:1h",
    }
    # Re-running the scan must not create duplicates.
    enqueue_reminders(db, now=NOW)
    enqueue_reminders(db, now=NOW + timedelta(minutes=1))
    assert _count(db, template="lesson_reminder") == 2


# --------------------------------------------------------------------------- #
# Low-balance hook (CO-K03)                                                    #
# --------------------------------------------------------------------------- #
def test_low_balance_reminder_dedupes_per_threshold(db):
    org = _org(db)
    student = _student(db, org.id)
    a = low_balance_reminder(
        db,
        org_id=org.id,
        student_id=student.id,
        recipient="p@example.com",
        balance=5,
        threshold=5,
    )
    again = low_balance_reminder(
        db,
        org_id=org.id,
        student_id=student.id,
        recipient="p@example.com",
        balance=4,
        threshold=5,
    )
    assert a.id == again.id  # same threshold -> no second send

    lower = low_balance_reminder(
        db,
        org_id=org.id,
        student_id=student.id,
        recipient="p@example.com",
        balance=2,
        threshold=2,
    )
    assert lower.id != a.id  # crossing a lower threshold notifies again
    assert _count(db, template="low_balance") == 2


def test_default_registry_has_email_adapter():
    from app.models.enums import NotificationChannel

    adapter = default_registry.get(NotificationChannel.email)
    assert isinstance(adapter, ConsoleEmailAdapter)


# --------------------------------------------------------------------------- #
# Router (org-scoped outbox + dev triggers)                                    #
# --------------------------------------------------------------------------- #
def _register(client, email="owner@example.com", org="Acme Tutoring"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "name": "Owner",
            "orgName": org,
        },
    ).json()


def _auth(reg):
    return {"Authorization": f"Bearer {reg['token']}"}


def test_router_enqueue_list_and_process(client):
    reg = _register(client)
    body = {
        "template": "lesson_reminder",
        "recipient": "sam@example.com",
        "payload": {"lessonId": "x"},
        "dedupeKey": "router-1",
    }
    r = client.post("/api/v1/notifications", json=body, headers=_auth(reg))
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "pending"
    assert r.json()["dedupeKey"] == "router-1"

    # Idempotent: same dedupeKey returns the same row.
    again = client.post("/api/v1/notifications", json=body, headers=_auth(reg))
    assert again.json()["id"] == r.json()["id"]

    listed = client.get("/api/v1/notifications", headers=_auth(reg))
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1

    # Flush, then status filters reflect the transition.
    run = client.post("/api/v1/notifications/process", headers=_auth(reg))
    assert run.status_code == 200, run.text
    assert run.json()["sent"] == 1

    sent = client.get(
        "/api/v1/notifications?status=sent", headers=_auth(reg)
    ).json()["items"]
    pending = client.get(
        "/api/v1/notifications?status=pending", headers=_auth(reg)
    ).json()["items"]
    assert len(sent) == 1
    assert pending == []


def test_router_outbox_is_org_scoped(client):
    a = _register(client, "a@example.com", "Org A")
    b = _register(client, "b@example.com", "Org B")
    client.post(
        "/api/v1/notifications",
        json={
            "template": "t",
            "recipient": "a@example.com",
            "dedupeKey": "org-a-1",
        },
        headers=_auth(a),
    )
    # Org B sees none of Org A's outbox.
    assert (
        client.get("/api/v1/notifications", headers=_auth(b)).json()["items"]
        == []
    )


def test_dispatcher_uuid_typing(db):
    """org_id round-trips as a real UUID on the persisted row."""
    org = _org(db)
    note = notify(
        db,
        org_id=org.id,
        template="t",
        recipient="a@example.com",
        dedupe_key="k-uuid",
    )
    assert isinstance(note.org_id, uuid.UUID)
    assert note.org_id == org.id
