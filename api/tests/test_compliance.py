"""CO-X03 compliance: org-scoped data export + owner-only account hard-delete.

Covers (a) export is org-scoped (two orgs, A's export contains only A's rows),
(b) a non-owner coach cannot delete (403), (c) an owner delete erases all of the
org's data while other orgs are untouched, (d) confirmation mismatch is rejected.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, time
from decimal import Decimal

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models import (
    CreditLedger,
    CreditPack,
    Guardian,
    ImportJob,
    Invoice,
    Lesson,
    LessonNote,
    Notification,
    Payment,
    RecurrenceRule,
    ShareLink,
    Student,
    User,
)
from app.models.enums import (
    ImportStatus,
    LedgerReason,
    LessonStatus,
    NotificationChannel,
    PaymentMethod,
    RecurrenceFreq,
    UserRole,
)


def _register(client, email, org):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "name": "Owner",
            "orgName": org,
        },
    ).json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_full_org(db, org_id: uuid.UUID, coach_id: uuid.UUID, label: str) -> dict:
    """Seed one row in every exportable child table for ``org_id``."""
    student = Student(org_id=org_id, name=f"Student {label}")
    db.add(student)
    db.flush()

    guardian = Guardian(org_id=org_id, student_id=student.id, name=f"Guardian {label}")
    rule = RecurrenceRule(
        org_id=org_id,
        freq=RecurrenceFreq.weekly,
        interval=1,
        byweekday=[0],
        start_date=datetime.now(UTC).date(),
        start_time=time(9, 0),
        duration_min=60,
    )
    db.add_all([guardian, rule])
    db.flush()

    lesson = Lesson(
        org_id=org_id,
        student_id=student.id,
        coach_id=coach_id,
        recurrence_id=rule.id,
        starts_at=datetime.now(UTC),
        duration_min=60,
        status=LessonStatus.scheduled,
    )
    pack = CreditPack(
        org_id=org_id,
        student_id=student.id,
        name=f"Pack {label}",
        total_sessions=10,
        price_per_session=Decimal("50.00"),
    )
    db.add_all([lesson, pack])
    db.flush()

    db.add_all(
        [
            CreditLedger(
                org_id=org_id,
                student_id=student.id,
                pack_id=pack.id,
                lesson_id=lesson.id,
                delta=10,
                reason=LedgerReason.purchase,
            ),
            Payment(
                org_id=org_id,
                student_id=student.id,
                amount=Decimal("500.00"),
                method=PaymentMethod.cash,
                pack_id=pack.id,
            ),
            Invoice(
                org_id=org_id,
                student_id=student.id,
                number=1,
                line_items=[],
                subtotal=Decimal("500.00"),
                total=Decimal("500.00"),
            ),
            Notification(
                org_id=org_id,
                channel=NotificationChannel.email,
                template="reminder",
                recipient="x@example.com",
                dedupe_key=f"dedupe-{label}",
            ),
            LessonNote(org_id=org_id, lesson_id=lesson.id, student_id=student.id),
            ShareLink(org_id=org_id, student_id=student.id, token=f"tok-{label}"),
            ImportJob(org_id=org_id, raw_input="raw", status=ImportStatus.parsing),
        ]
    )
    db.commit()
    return {"student_id": student.id}


def _make_coach(db, org_id: uuid.UUID) -> User:
    coach = User(
        org_id=org_id,
        email=f"coach-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("supersecret1"),
        name="Coach",
        role=UserRole.coach,
        is_active=True,
    )
    db.add(coach)
    db.commit()
    db.refresh(coach)
    return coach


# --- (a) export is org-scoped --------------------------------------------------


def test_export_returns_only_current_org_data(client, db):
    a = _register(client, "a@example.com", "Org A")
    b = _register(client, "b@example.com", "Org B")
    org_a = uuid.UUID(a["user"]["orgId"])
    org_b = uuid.UUID(b["user"]["orgId"])

    _seed_full_org(db, org_a, uuid.UUID(a["user"]["id"]), "A")
    _seed_full_org(db, org_b, uuid.UUID(b["user"]["id"]), "B")

    resp = client.get("/api/v1/compliance/export", headers=_auth(a["token"]))
    assert resp.status_code == 200
    doc = resp.json()

    # The org object is A's, not B's.
    assert doc["organization"]["name"] == "Org A"
    assert doc["organization"]["id"] == str(org_a)

    # Every student in the export belongs to org A only.
    assert [s["name"] for s in doc["students"]] == ["Student A"]
    assert all(s["org_id"] == str(org_a) for s in doc["students"])

    # Cross-org isolation: org B's ids must never appear anywhere in A's dump.
    all_org_ids = {
        row["org_id"]
        for key, rows in doc.items()
        if isinstance(rows, list)
        for row in rows
    }
    assert all_org_ids == {str(org_a)}
    assert str(org_b) not in all_org_ids

    # Every exportable collection is populated for A.
    for key in (
        "users",
        "students",
        "guardians",
        "recurrence_rules",
        "lessons",
        "credit_packs",
        "credit_ledger",
        "payments",
        "invoices",
        "notifications",
        "lesson_notes",
        "share_links",
        "import_jobs",
    ):
        assert len(doc[key]) >= 1, key


def test_export_serializes_decimals_as_strings(client, db):
    a = _register(client, "a@example.com", "Org A")
    org_a = uuid.UUID(a["user"]["orgId"])
    _seed_full_org(db, org_a, uuid.UUID(a["user"]["id"]), "A")

    doc = client.get(
        "/api/v1/compliance/export", headers=_auth(a["token"])
    ).json()
    assert doc["payments"][0]["amount"] == "500.00"
    assert doc["credit_packs"][0]["price_per_session"] == "50.00"


def test_export_requires_auth(client):
    assert client.get("/api/v1/compliance/export").status_code == 401


# --- (b) non-owner cannot delete ----------------------------------------------


def test_coach_cannot_delete_account(client, db):
    a = _register(client, "a@example.com", "Org A")
    org_a = uuid.UUID(a["user"]["orgId"])
    coach = _make_coach(db, org_a)
    coach_token = create_access_token(
        user_id=str(coach.id), org_id=str(org_a), role=coach.role.value
    )

    resp = client.request(
        "DELETE",
        "/api/v1/compliance/account",
        headers=_auth(coach_token),
        json={"confirm": "Org A"},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"
    # Org A's data is untouched.
    assert db.get(User, coach.id) is not None


# --- (d) confirmation mismatch ------------------------------------------------


def test_delete_rejects_confirmation_mismatch(client, db):
    a = _register(client, "a@example.com", "Org A")
    org_a = uuid.UUID(a["user"]["orgId"])
    _seed_full_org(db, org_a, uuid.UUID(a["user"]["id"]), "A")

    resp = client.request(
        "DELETE",
        "/api/v1/compliance/account",
        headers=_auth(a["token"]),
        json={"confirm": "Wrong Name"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "confirmation_mismatch"
    # Nothing deleted.
    assert db.scalar(
        select(Student).where(Student.org_id == org_a)
    ) is not None


# --- (c) owner delete erases org, others untouched ----------------------------


def test_owner_delete_erases_all_org_data_and_leaves_others(client, db):
    a = _register(client, "a@example.com", "Org A")
    b = _register(client, "b@example.com", "Org B")
    org_a = uuid.UUID(a["user"]["orgId"])
    org_b = uuid.UUID(b["user"]["orgId"])
    _seed_full_org(db, org_a, uuid.UUID(a["user"]["id"]), "A")
    _seed_full_org(db, org_b, uuid.UUID(b["user"]["id"]), "B")

    resp = client.request(
        "DELETE",
        "/api/v1/compliance/account",
        headers=_auth(a["token"]),
        json={"confirm": "Org A"},
    )
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["orgId"] == str(org_a)
    assert summary["deleted"]["students"] == 1
    assert summary["deleted"]["organizations"] == 1

    models = (
        User,
        Student,
        Guardian,
        RecurrenceRule,
        Lesson,
        CreditPack,
        CreditLedger,
        Payment,
        Invoice,
        Notification,
        LessonNote,
        ShareLink,
        ImportJob,
    )
    # Org A wiped across every table; org B fully intact.
    for model in models:
        a_rows = db.scalars(select(model).where(model.org_id == org_a)).all()
        b_rows = db.scalars(select(model).where(model.org_id == org_b)).all()
        assert a_rows == [], model.__tablename__
        assert len(b_rows) >= 1, model.__tablename__
