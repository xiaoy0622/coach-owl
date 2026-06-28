"""Cross-domain linkage tests: scheduling ↔ credits ↔ notifications (CO-C03 /
CO-K03).

These exercise the hooks the Wave-2 services left open:
- completing a lesson deducts exactly one credit and is idempotent,
- the deduction policy for completed / no_show / cancelled,
- cancel + reschedule write channel-agnostic outbox notifications (deduped),
- a deduct that drops the balance to/under the threshold raises a single
  low-balance reminder.

They go through the FastAPI client and the real org-scoped services, asserting
the §1.5 ledger invariant stays intact (balance == SUM(delta); never stored).
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models.notifications import Notification
from app.models.student import Student

# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #


def _register(client, email="coach@example.com", org="Acme Tutoring"):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "name": "Coach",
            "orgName": org,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _auth(reg):
    return {"Authorization": f"Bearer {reg['token']}"}


def _make_student(db, org_id, *, name="Sam Student", email="sam@example.com"):
    student = Student(org_id=uuid.UUID(str(org_id)), name=name, email=email)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student.id


def _buy_pack(client, reg, student_id, sessions):
    r = client.post(
        "/api/v1/credits/packs",
        headers=_auth(reg),
        json={
            "studentId": str(student_id),
            "name": f"{sessions}-pack",
            "totalSessions": sessions,
            "pricePerSession": "50.00",
        },
    )
    assert r.status_code == 201, r.text


def _create_lesson(client, reg, student_id, coach_id, starts_at):
    r = client.post(
        "/api/v1/lessons",
        headers=_auth(reg),
        json={
            "studentId": str(student_id),
            "coachId": coach_id,
            "startsAt": starts_at,
            "durationMin": 60,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["items"][0]


def _balance(client, reg, student_id):
    return client.get(
        f"/api/v1/credits/balance/{student_id}", headers=_auth(reg)
    ).json()["balance"]


def _ledger(client, reg, student_id):
    return client.get(
        f"/api/v1/credits/ledger?studentId={student_id}", headers=_auth(reg)
    ).json()["items"]


def _notif_count(db, **where) -> int:
    stmt = select(func.count()).select_from(Notification)
    for col, val in where.items():
        stmt = stmt.where(getattr(Notification, col) == val)
    return db.scalar(stmt)


def _notif(db, **where) -> Notification | None:
    stmt = select(Notification)
    for col, val in where.items():
        stmt = stmt.where(getattr(Notification, col) == val)
    return db.scalar(stmt)


# --------------------------------------------------------------------------- #
# Lesson completion → credit deduction (CO-C03)                                #
# --------------------------------------------------------------------------- #
def test_completing_lesson_deducts_one_credit(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)
    _buy_pack(client, reg, student_id, 10)
    lesson = _create_lesson(client, reg, student_id, coach_id, "2026-05-12T06:00:00Z")

    r = client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={"status": "completed"},
        headers=_auth(reg),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed"
    assert r.json()["creditDeducted"] is True

    # Exactly one -1 deduct entry, tagged with the lesson, balance 10 -> 9.
    assert _balance(client, reg, student_id) == 9
    ledger = _ledger(client, reg, student_id)
    deducts = [e for e in ledger if e["reason"] == "deduct"]
    assert len(deducts) == 1
    assert deducts[0]["delta"] == -1
    assert deducts[0]["lessonId"] == lesson["id"]
    # §1.5 invariant: balance == SUM(delta).
    assert _balance(client, reg, student_id) == sum(e["delta"] for e in ledger)


def test_recompleting_lesson_does_not_double_deduct(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)
    _buy_pack(client, reg, student_id, 10)
    lesson = _create_lesson(client, reg, student_id, coach_id, "2026-05-12T06:00:00Z")

    for _ in range(3):
        r = client.patch(
            f"/api/v1/lessons/{lesson['id']}",
            json={"status": "completed"},
            headers=_auth(reg),
        )
        assert r.status_code == 200, r.text
        assert r.json()["creditDeducted"] is True

    # Idempotent: still exactly one deduct, balance still 9.
    ledger = _ledger(client, reg, student_id)
    assert len([e for e in ledger if e["reason"] == "deduct"]) == 1
    assert _balance(client, reg, student_id) == 9


def test_completion_opt_out_skips_deduction(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)
    _buy_pack(client, reg, student_id, 10)
    lesson = _create_lesson(client, reg, student_id, coach_id, "2026-05-12T06:00:00Z")

    r = client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={"status": "completed", "deductCredit": False},
        headers=_auth(reg),
    )
    assert r.status_code == 200, r.text
    assert r.json()["creditDeducted"] is False
    assert _balance(client, reg, student_id) == 10
    assert [e for e in _ledger(client, reg, student_id) if e["reason"] == "deduct"] == []


def test_completion_without_balance_is_rejected_and_rolls_back(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)  # no pack -> balance 0
    lesson = _create_lesson(client, reg, student_id, coach_id, "2026-05-12T06:00:00Z")

    r = client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={"status": "completed"},
        headers=_auth(reg),
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "insufficient_balance"

    # Atomic: the lesson stayed scheduled (status change rolled back with it).
    got = client.get(f"/api/v1/lessons/{lesson['id']}", headers=_auth(reg)).json()
    assert got["status"] == "scheduled"
    assert got["creditDeducted"] is False


# --------------------------------------------------------------------------- #
# cancel / no_show deduction policy                                            #
# --------------------------------------------------------------------------- #
def test_cancel_does_not_deduct(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)
    _buy_pack(client, reg, student_id, 10)
    lesson = _create_lesson(client, reg, student_id, coach_id, "2026-05-12T06:00:00Z")

    r = client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={"status": "cancelled", "deductCredit": True},
        headers=_auth(reg),
    )
    assert r.status_code == 200, r.text
    assert r.json()["creditDeducted"] is False
    assert _balance(client, reg, student_id) == 10


def test_no_show_deducts_only_with_flag(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    _buy = _buy_pack
    # Without the flag: no deduction.
    s1 = _make_student(db, org_id, email="a@example.com")
    _buy(client, reg, s1, 10)
    l1 = _create_lesson(client, reg, s1, coach_id, "2026-05-12T06:00:00Z")
    r1 = client.patch(
        f"/api/v1/lessons/{l1['id']}",
        json={"status": "no_show"},
        headers=_auth(reg),
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["creditDeducted"] is False
    assert _balance(client, reg, s1) == 10

    # With the flag: one deduction.
    s2 = _make_student(db, org_id, email="b@example.com")
    _buy(client, reg, s2, 10)
    l2 = _create_lesson(client, reg, s2, coach_id, "2026-05-13T06:00:00Z")
    r2 = client.patch(
        f"/api/v1/lessons/{l2['id']}",
        json={"status": "no_show", "deductCredit": True},
        headers=_auth(reg),
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["creditDeducted"] is True
    assert _balance(client, reg, s2) == 9


# --------------------------------------------------------------------------- #
# cancel / reschedule → notification outbox (CO-C03)                           #
# --------------------------------------------------------------------------- #
def test_cancel_writes_lesson_cancelled_outbox_row(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id, email="sam@example.com")
    lesson = _create_lesson(client, reg, student_id, coach_id, "2026-05-12T06:00:00Z")

    r = client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={"status": "cancelled", "cancelReason": "Student sick"},
        headers=_auth(reg),
    )
    assert r.status_code == 200, r.text

    note = _notif(db, template="lesson_cancelled")
    assert note is not None
    assert note.recipient == "sam@example.com"
    assert note.dedupe_key == f"lesson:{lesson['id']}:cancelled"
    assert note.payload["lessonId"] == lesson["id"]
    assert _notif_count(db, template="lesson_cancelled") == 1


def test_cancel_falls_back_to_coach_recipient(client, db):
    reg = _register(client, email="thecoach@example.com")
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id, email=None)  # no student email
    lesson = _create_lesson(client, reg, student_id, coach_id, "2026-05-12T06:00:00Z")

    client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={"status": "cancelled"},
        headers=_auth(reg),
    )
    note = _notif(db, template="lesson_cancelled")
    assert note is not None
    assert note.recipient == "thecoach@example.com"


def test_reschedule_writes_lesson_rescheduled_outbox_row(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id, email="sam@example.com")
    lesson = _create_lesson(client, reg, student_id, coach_id, "2026-05-12T06:00:00Z")

    r = client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={"startsAt": "2026-05-13T06:00:00Z"},
        headers=_auth(reg),
    )
    assert r.status_code == 200, r.text
    assert _notif_count(db, template="lesson_rescheduled") == 1
    note = _notif(db, template="lesson_rescheduled")
    assert note.dedupe_key.startswith(f"lesson:{lesson['id']}:rescheduled:")

    # Replaying the same reschedule does not enqueue a second notice.
    client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={"startsAt": "2026-05-13T06:00:00Z"},
        headers=_auth(reg),
    )
    assert _notif_count(db, template="lesson_rescheduled") == 1


# --------------------------------------------------------------------------- #
# low-balance reminder on threshold crossing (CO-K03)                          #
# --------------------------------------------------------------------------- #
def test_deduct_crossing_threshold_writes_one_low_balance_row(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id, email="sam@example.com")
    _buy_pack(client, reg, student_id, 3)  # threshold default = 2

    # Complete lesson 1: balance 3 -> 2 (== threshold) -> reminder fires.
    l1 = _create_lesson(client, reg, student_id, coach_id, "2026-05-12T06:00:00Z")
    client.patch(
        f"/api/v1/lessons/{l1['id']}",
        json={"status": "completed"},
        headers=_auth(reg),
    )
    assert _balance(client, reg, student_id) == 2
    assert _notif_count(db, template="low_balance") == 1

    note = _notif(db, template="low_balance")
    assert note.recipient == "sam@example.com"
    assert note.dedupe_key == f"student:{student_id}:low_balance:2"

    # Complete lesson 2: balance 2 -> 1 (still <= threshold) but same threshold
    # key -> deduped, no second reminder.
    l2 = _create_lesson(client, reg, student_id, coach_id, "2026-05-13T06:00:00Z")
    client.patch(
        f"/api/v1/lessons/{l2['id']}",
        json={"status": "completed"},
        headers=_auth(reg),
    )
    assert _balance(client, reg, student_id) == 1
    assert _notif_count(db, template="low_balance") == 1


def test_deduct_above_threshold_writes_no_reminder(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id, email="sam@example.com")
    _buy_pack(client, reg, student_id, 10)  # balance 10 -> 9, well above 2
    lesson = _create_lesson(client, reg, student_id, coach_id, "2026-05-12T06:00:00Z")

    client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={"status": "completed"},
        headers=_auth(reg),
    )
    assert _balance(client, reg, student_id) == 9
    assert _notif_count(db, template="low_balance") == 0
