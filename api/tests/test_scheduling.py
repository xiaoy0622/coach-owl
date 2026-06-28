"""Scheduling: recurrence engine (DST) + lessons CRUD/conflict/transitions.

CO-C01/C02/C03. The engine tests are pure-function unit tests; the API tests go
through the FastAPI client and the org-scoped service layer.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time

from app.models.student import Student
from app.schemas.scheduling import RecurrenceRuleCreate
from app.services.scheduling import Occurrence, expand_recurrence

SYDNEY = "Australia/Sydney"


# --------------------------------------------------------------------------- #
# CO-C01 — recurrence engine (pure, DST-correct)                               #
# --------------------------------------------------------------------------- #
def _rule(**kw) -> RecurrenceRuleCreate:
    base = dict(
        byweekday=[],
        start_date=date(2026, 5, 4),  # a Monday
        end_date=None,
        start_time=time(16, 0),
        duration_min=60,
    )
    base.update(kw)
    return RecurrenceRuleCreate(**base)


def test_weekly_single_day_bounded():
    rule = _rule(byweekday=[1], start_date=date(2026, 5, 1), end_date=date(2026, 5, 31))
    occ = expand_recurrence(rule, SYDNEY)
    # Tuesdays in May 2026: 5, 12, 19, 26.
    days = [o.starts_at.astimezone(UTC).date() for o in occ]
    assert all(o.duration_min == 60 for o in occ)
    assert len(occ) == 4
    # 16:00 Sydney standard time (AEST, UTC+10) -> 06:00 UTC.
    assert occ[0].starts_at == datetime(2026, 5, 5, 6, 0, tzinfo=UTC)
    assert days[-1] == date(2026, 5, 26)


def test_multi_weekday():
    rule = _rule(
        byweekday=[1, 3],  # Tue + Thu
        start_date=date(2026, 5, 4),
        end_date=date(2026, 5, 17),
    )
    occ = expand_recurrence(rule, SYDNEY)
    # Tue 5, Thu 7, Tue 12, Thu 14 (within range, sorted).
    local_days = [o.starts_at.astimezone(UTC).isoformat() for o in occ]
    assert len(occ) == 4
    # Sorted ascending by time.
    assert [o.starts_at for o in occ] == sorted(o.starts_at for o in occ)
    assert local_days == sorted(local_days)


def test_interval_every_two_weeks():
    rule = _rule(
        byweekday=[0],  # Monday
        start_date=date(2026, 5, 4),
        end_date=date(2026, 6, 30),
        interval=2,
    )
    occ = expand_recurrence(rule, SYDNEY)
    days = [o.starts_at.astimezone(UTC).date() for o in occ]
    # Every 2nd Monday from 4 May: 4, 18 May; 1, 15, 29 Jun.
    assert days == [
        date(2026, 5, 4),
        date(2026, 5, 18),
        date(2026, 6, 1),
        date(2026, 6, 15),
        date(2026, 6, 29),
    ]


def test_dst_transition_keeps_local_wall_time():
    """Across the AEDT->AEST autumn change (first Sunday April 2026 = 5 Apr),
    a weekly 16:00 Sydney lesson stays 16:00 local while its UTC time shifts."""
    rule = _rule(
        byweekday=[2],  # Wednesday
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 15),
        start_time=time(16, 0),
    )
    occ = expand_recurrence(rule, SYDNEY)
    # Wednesdays 1, 8, 15 April. DST ends Sun 5 Apr 2026 (AEDT+11 -> AEST+10).
    assert len(occ) == 3
    # 1 Apr is still AEDT (UTC+11): 16:00 -> 05:00 UTC.
    assert occ[0].starts_at == datetime(2026, 4, 1, 5, 0, tzinfo=UTC)
    # 8 & 15 Apr are AEST (UTC+10): 16:00 -> 06:00 UTC.
    assert occ[1].starts_at == datetime(2026, 4, 8, 6, 0, tzinfo=UTC)
    assert occ[2].starts_at == datetime(2026, 4, 15, 6, 0, tzinfo=UTC)
    # Local wall-clock is identical (16:00) on every occurrence.
    from zoneinfo import ZoneInfo

    syd = ZoneInfo(SYDNEY)
    assert {o.starts_at.astimezone(syd).timetz().replace(tzinfo=None) for o in occ} == {
        time(16, 0)
    }


def test_spring_forward_transition():
    """Across the AEST->AEDT spring change (first Sunday October 2026 = 4 Oct)."""
    rule = _rule(
        byweekday=[1],  # Tuesday
        start_date=date(2026, 9, 29),
        end_date=date(2026, 10, 13),
        start_time=time(16, 0),
    )
    occ = expand_recurrence(rule, SYDNEY)
    # 29 Sep AEST (UTC+10) -> 06:00 UTC; 6 & 13 Oct AEDT (UTC+11) -> 05:00 UTC.
    assert occ[0].starts_at == datetime(2026, 9, 29, 6, 0, tzinfo=UTC)
    assert occ[1].starts_at == datetime(2026, 10, 6, 5, 0, tzinfo=UTC)
    assert occ[2].starts_at == datetime(2026, 10, 13, 5, 0, tzinfo=UTC)


def test_empty_byweekday_defaults_to_start_weekday():
    rule = _rule(byweekday=[], start_date=date(2026, 5, 6), end_date=date(2026, 5, 27))
    occ = expand_recurrence(rule, SYDNEY)
    # 6 May 2026 is a Wednesday -> every Wednesday: 6, 13, 20, 27.
    days = [o.starts_at.astimezone(UTC).date() for o in occ]
    assert days == [
        date(2026, 5, 6),
        date(2026, 5, 13),
        date(2026, 5, 20),
        date(2026, 5, 27),
    ]


def test_open_ended_rule_is_capped():
    rule = _rule(byweekday=[0], start_date=date(2026, 5, 4), end_date=None)
    occ = expand_recurrence(rule, SYDNEY, limit=10)
    assert len(occ) == 10
    assert isinstance(occ[0], Occurrence)


# --------------------------------------------------------------------------- #
# CO-C02/C03 — API: create / list / conflict / transitions                     #
# --------------------------------------------------------------------------- #
def _register(client, email="coach@example.com", org="Acme Tutoring"):
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "name": "Coach",
            "orgName": org,
        },
    ).json()


def _make_student(db, org_id: uuid.UUID, name="Sam Student") -> uuid.UUID:
    student = Student(org_id=uuid.UUID(str(org_id)), name=name)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student.id


def _auth(reg):
    return {"Authorization": f"Bearer {reg['token']}"}


def test_create_single_lesson(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)

    body = {
        "studentId": str(student_id),
        "coachId": coach_id,
        "startsAt": "2026-05-12T06:00:00Z",
        "durationMin": 60,
    }
    r = client.post("/api/v1/lessons", json=body, headers=_auth(reg))
    assert r.status_code == 201, r.text
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "scheduled"
    assert items[0]["recurrenceId"] is None
    assert items[0]["creditDeducted"] is False


def test_create_recurring_series_expands(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)

    body = {
        "studentId": str(student_id),
        "coachId": coach_id,
        "startsAt": "2026-05-05T06:00:00Z",
        "durationMin": 60,
        "recurrence": {
            "freq": "weekly",
            "interval": 1,
            "byweekday": [1],  # Tuesday
            "startDate": "2026-05-01",
            "endDate": "2026-05-31",
            "startTime": "16:00:00",
            "durationMin": 60,
        },
    }
    r = client.post("/api/v1/lessons", json=body, headers=_auth(reg))
    assert r.status_code == 201, r.text
    items = r.json()["items"]
    assert len(items) == 4  # 4 Tuesdays in May 2026
    assert all(it["recurrenceId"] for it in items)
    assert {it["recurrenceId"] for it in items} == {items[0]["recurrenceId"]}


def test_conflict_same_coach_overlap(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)

    base = {
        "studentId": str(student_id),
        "coachId": coach_id,
        "startsAt": "2026-05-12T06:00:00Z",
        "durationMin": 60,
    }
    created = client.post("/api/v1/lessons", json=base, headers=_auth(reg))
    assert created.status_code == 201

    # Overlaps the first lesson by 30 min for the same coach.
    overlap = {**base, "startsAt": "2026-05-12T06:30:00Z"}
    r = client.post("/api/v1/lessons", json=overlap, headers=_auth(reg))
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "lesson_conflict"
    assert len(r.json()["error"]["details"]) == 1


def test_no_conflict_when_adjacent(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)
    base = {
        "studentId": str(student_id),
        "coachId": coach_id,
        "startsAt": "2026-05-12T06:00:00Z",
        "durationMin": 60,
    }
    created = client.post("/api/v1/lessons", json=base, headers=_auth(reg))
    assert created.status_code == 201
    # Starts exactly when the first ends -> no overlap.
    adjacent = {**base, "startsAt": "2026-05-12T07:00:00Z"}
    r = client.post("/api/v1/lessons", json=adjacent, headers=_auth(reg))
    assert r.status_code == 201, r.text


def test_list_by_range(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)
    for day in (10, 12, 20):
        client.post(
            "/api/v1/lessons",
            json={
                "studentId": str(student_id),
                "coachId": coach_id,
                "startsAt": f"2026-05-{day}T06:00:00Z",
                "durationMin": 60,
            },
            headers=_auth(reg),
        )
    r = client.get(
        "/api/v1/lessons?from=2026-05-11T00:00:00Z&to=2026-05-15T00:00:00Z",
        headers=_auth(reg),
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["startsAt"].startswith("2026-05-12")


def test_reschedule_and_conflict_on_reschedule(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)
    first = client.post(
        "/api/v1/lessons",
        json={
            "studentId": str(student_id),
            "coachId": coach_id,
            "startsAt": "2026-05-12T06:00:00Z",
            "durationMin": 60,
        },
        headers=_auth(reg),
    ).json()["items"][0]
    second = client.post(
        "/api/v1/lessons",
        json={
            "studentId": str(student_id),
            "coachId": coach_id,
            "startsAt": "2026-05-12T08:00:00Z",
            "durationMin": 60,
        },
        headers=_auth(reg),
    ).json()["items"][0]

    # Reschedule second onto first -> conflict.
    r = client.patch(
        f"/api/v1/lessons/{second['id']}",
        json={"startsAt": "2026-05-12T06:30:00Z"},
        headers=_auth(reg),
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "lesson_conflict"

    # Reschedule to a free slot -> ok.
    r = client.patch(
        f"/api/v1/lessons/{second['id']}",
        json={"startsAt": "2026-05-13T06:00:00Z"},
        headers=_auth(reg),
    )
    assert r.status_code == 200, r.text
    assert r.json()["startsAt"].startswith("2026-05-13")
    assert first["id"]  # untouched


def test_cancel_and_no_show_transitions(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)
    lesson = client.post(
        "/api/v1/lessons",
        json={
            "studentId": str(student_id),
            "coachId": coach_id,
            "startsAt": "2026-05-12T06:00:00Z",
            "durationMin": 60,
        },
        headers=_auth(reg),
    ).json()["items"][0]

    r = client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={"status": "cancelled", "cancelReason": "Student sick"},
        headers=_auth(reg),
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"
    assert r.json()["cancelReason"] == "Student sick"

    # cancelled is terminal -> cannot move to no_show.
    r = client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={"status": "no_show"},
        headers=_auth(reg),
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "invalid_transition"


def test_cannot_reschedule_completed_lesson(client, db):
    reg = _register(client)
    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student_id = _make_student(db, org_id)
    lesson = client.post(
        "/api/v1/lessons",
        json={
            "studentId": str(student_id),
            "coachId": coach_id,
            "startsAt": "2026-05-12T06:00:00Z",
            "durationMin": 60,
        },
        headers=_auth(reg),
    ).json()["items"][0]
    assert (
        client.patch(
            f"/api/v1/lessons/{lesson['id']}",
            json={"status": "completed"},
            headers=_auth(reg),
        ).status_code
        == 200
    )
    r = client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={"startsAt": "2026-05-13T06:00:00Z"},
        headers=_auth(reg),
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "invalid_transition"


def test_tenant_isolation_on_lessons(client, db):
    a = _register(client, "a@example.com", "Org A")
    b = _register(client, "b@example.com", "Org B")
    org_a = a["user"]["orgId"]
    student_a = _make_student(db, org_a)
    client.post(
        "/api/v1/lessons",
        json={
            "studentId": str(student_a),
            "coachId": a["user"]["id"],
            "startsAt": "2026-05-12T06:00:00Z",
            "durationMin": 60,
        },
        headers=_auth(a),
    )
    # Org B sees none of Org A's lessons.
    r = client.get("/api/v1/lessons", headers=_auth(b))
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_get_lesson_not_found(client):
    reg = _register(client)
    r = client.get(f"/api/v1/lessons/{uuid.uuid4()}", headers=_auth(reg))
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
