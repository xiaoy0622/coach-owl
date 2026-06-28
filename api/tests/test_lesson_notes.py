"""Post-lesson notes: AI structuring + confirm-before-save CRUD (CO-A02).

The structurer tests are pure-function (no network, no API key). The API tests go
through the FastAPI client and the org-scoped service layer, and assert the
confirm gate: ``/structure`` never persists; saving stores the confirmed data.
"""
from __future__ import annotations

import uuid

from app.ai.note_structurer import structure_note


# --------------------------------------------------------------------------- #
# Structurer — deterministic heuristic shape (no network)                      #
# --------------------------------------------------------------------------- #
def test_structure_returns_expected_shape():
    out = structure_note("did fractions and decimals")
    assert set(out.keys()) == {"topics", "progress", "homework"}
    assert isinstance(out["topics"], list)
    assert out["progress"] is None or isinstance(out["progress"], str)
    assert out["homework"] is None or isinstance(out["homework"], str)


def test_structure_empty_input():
    out = structure_note("")
    assert out == {"topics": [], "progress": None, "homework": None}


def test_structure_extracts_topics():
    out = structure_note("Covered fractions, decimals and percentages today")
    assert "fractions" in out["topics"]
    assert "decimals" in out["topics"]
    assert "percentages" in out["topics"]


def test_structure_detects_homework():
    out = structure_note(
        "Worked on long division. Homework: finish worksheet 3."
    )
    assert out["homework"] is not None
    assert "worksheet 3" in out["homework"].lower()
    # Homework text should not leak into topics.
    assert all("worksheet" not in t.lower() for t in out["topics"])


def test_structure_captures_progress():
    out = structure_note("Tom struggled with common denominators but improved")
    assert out["progress"] is not None
    assert "struggl" in out["progress"].lower()


def test_structure_parses_labelled_input():
    out = structure_note(
        "Topics: algebra, graphing\nProgress: confident with slopes\nHomework: ex 4.2"
    )
    assert out["topics"] == ["algebra", "graphing"]
    assert "confident" in out["progress"].lower()
    assert "4.2" in out["homework"]


# --------------------------------------------------------------------------- #
# API helpers                                                                  #
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


def _auth(reg):
    return {"Authorization": f"Bearer {reg['token']}"}


def _make_lesson(client, reg, db):
    """Create a student + a single lesson, returning (studentId, lessonId)."""
    from app.models.student import Student

    org_id = reg["user"]["orgId"]
    coach_id = reg["user"]["id"]
    student = Student(org_id=uuid.UUID(str(org_id)), name="Sam Student")
    db.add(student)
    db.commit()
    db.refresh(student)

    lesson = client.post(
        "/api/v1/lessons",
        json={
            "studentId": str(student.id),
            "coachId": coach_id,
            "startsAt": "2026-05-12T06:00:00Z",
            "durationMin": 60,
        },
        headers=_auth(reg),
    ).json()["items"][0]
    return str(student.id), lesson["id"]


# --------------------------------------------------------------------------- #
# /structure — AI candidate, never persists                                    #
# --------------------------------------------------------------------------- #
def test_structure_endpoint_returns_candidate_without_persisting(client, db):
    reg = _register(client)
    r = client.post(
        "/api/v1/lesson-notes/structure",
        json={"rawInput": "Covered fractions. Homework: worksheet 3."},
        headers=_auth(reg),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "fractions" in body["topics"]
    assert body["homework"] is not None

    # Confirm gate: nothing was written to the notes timeline.
    listed = client.get("/api/v1/lesson-notes", headers=_auth(reg))
    assert listed.status_code == 200
    assert listed.json()["items"] == []


def test_structure_endpoint_requires_auth(client):
    r = client.post(
        "/api/v1/lesson-notes/structure", json={"rawInput": "anything"}
    )
    assert r.status_code == 401


# --------------------------------------------------------------------------- #
# Save persists the confirmed structure                                        #
# --------------------------------------------------------------------------- #
def test_save_persists_confirmed_note(client, db):
    reg = _register(client)
    student_id, lesson_id = _make_lesson(client, reg, db)

    payload = {
        "lessonId": lesson_id,
        "studentId": student_id,
        "rawInput": "did fractions, Tom improved",
        "structured": {
            "topics": ["fractions", "decimals"],
            "progress": "Improving steadily",
            "homework": "Worksheet 3",
        },
        "source": "text",
    }
    r = client.post("/api/v1/lesson-notes", json=payload, headers=_auth(reg))
    assert r.status_code == 201, r.text
    saved = r.json()
    assert saved["structured"]["topics"] == ["fractions", "decimals"]
    assert saved["structured"]["homework"] == "Worksheet 3"
    assert saved["lessonId"] == lesson_id

    # It now appears in the student's timeline.
    listed = client.get(
        f"/api/v1/lesson-notes?studentId={student_id}", headers=_auth(reg)
    ).json()
    assert len(listed["items"]) == 1
    assert listed["items"][0]["id"] == saved["id"]


def test_save_rejects_student_lesson_mismatch(client, db):
    reg = _register(client)
    _student_id, lesson_id = _make_lesson(client, reg, db)
    r = client.post(
        "/api/v1/lesson-notes",
        json={
            "lessonId": lesson_id,
            "studentId": str(uuid.uuid4()),  # not this lesson's student
            "structured": {"topics": ["x"]},
        },
        headers=_auth(reg),
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "student_mismatch"


def test_save_unknown_lesson_404(client):
    reg = _register(client)
    r = client.post(
        "/api/v1/lesson-notes",
        json={
            "lessonId": str(uuid.uuid4()),
            "studentId": str(uuid.uuid4()),
            "structured": {"topics": []},
        },
        headers=_auth(reg),
    )
    assert r.status_code == 404


def test_update_re_edits_saved_note(client, db):
    reg = _register(client)
    student_id, lesson_id = _make_lesson(client, reg, db)
    note = client.post(
        "/api/v1/lesson-notes",
        json={
            "lessonId": lesson_id,
            "studentId": student_id,
            "structured": {"topics": ["a"], "progress": "ok"},
        },
        headers=_auth(reg),
    ).json()

    r = client.patch(
        f"/api/v1/lesson-notes/{note['id']}",
        json={"structured": {"topics": ["a", "b"], "homework": "read ch.2"}},
        headers=_auth(reg),
    )
    assert r.status_code == 200, r.text
    assert r.json()["structured"]["topics"] == ["a", "b"]
    assert r.json()["structured"]["homework"] == "read ch.2"


def test_delete_note(client, db):
    reg = _register(client)
    student_id, lesson_id = _make_lesson(client, reg, db)
    note = client.post(
        "/api/v1/lesson-notes",
        json={
            "lessonId": lesson_id,
            "studentId": student_id,
            "structured": {"topics": ["a"]},
        },
        headers=_auth(reg),
    ).json()
    assert (
        client.delete(
            f"/api/v1/lesson-notes/{note['id']}", headers=_auth(reg)
        ).status_code
        == 204
    )
    assert (
        client.get(
            f"/api/v1/lesson-notes/{note['id']}", headers=_auth(reg)
        ).status_code
        == 404
    )


# --------------------------------------------------------------------------- #
# Org scoping                                                                  #
# --------------------------------------------------------------------------- #
def test_notes_are_org_scoped(client, db):
    a = _register(client, "a@example.com", "Org A")
    b = _register(client, "b@example.com", "Org B")
    student_id, lesson_id = _make_lesson(client, a, db)
    note = client.post(
        "/api/v1/lesson-notes",
        json={
            "lessonId": lesson_id,
            "studentId": student_id,
            "structured": {"topics": ["secret"]},
        },
        headers=_auth(a),
    ).json()

    # Org B sees none of Org A's notes and cannot fetch one by id.
    assert client.get("/api/v1/lesson-notes", headers=_auth(b)).json()["items"] == []
    assert (
        client.get(
            f"/api/v1/lesson-notes/{note['id']}", headers=_auth(b)
        ).status_code
        == 404
    )
