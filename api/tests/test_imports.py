"""Smart import: heuristic parse + confirm-before-commit (CO-S04)."""
from __future__ import annotations

from app.services import imports as svc


def _auth(client, email="owner@example.com", org="Acme"):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "name": "Owner",
            "orgName": org,
        },
    )
    return {"Authorization": f"Bearer {r.json()['token']}"}


# --- unit tests for the deterministic parser (no network) -------------------
def test_parse_csv_with_header():
    raw = (
        "Name,Email,Phone\n"
        "Ada Lovelace,ada@x.com,0400 123 456\n"
        "Grace Hopper,grace@navy.mil,0411222333"
    )
    out = svc.parse_text(raw)
    assert out["source"] == "csv"
    assert len(out["candidates"]) == 2
    c = out["candidates"][0]
    assert c["name"] == "Ada Lovelace"
    assert c["email"] == "ada@x.com"
    assert "0400 123 456" in c["phone"]


def test_parse_messy_column_order_and_guardian():
    raw = (
        "Phone;Guardian;Student Name;Parent Phone\n"
        "0400111222;Jane Smith;Tommy Smith;0400999888"
    )
    out = svc.parse_text(raw)
    c = out["candidates"][0]
    assert c["name"] == "Tommy Smith"
    assert "0400111222" in c["phone"]
    assert c["guardians"][0]["name"] == "Jane Smith"
    assert "0400999888" in c["guardians"][0]["phone"]
    assert c["guardians"][0]["isPrimary"] is True


def test_parse_freetext_with_schedule_and_contact():
    raw = "Sarah Lee sarah@mail.com 0422 333 444 Tue/Thu 4-5pm"
    out = svc.parse_text(raw)
    assert out["source"] == "text"
    c = out["candidates"][0]
    assert c["name"] == "Sarah Lee"
    assert c["email"] == "sarah@mail.com"
    assert c["phone"] is not None
    assert c["scheduleText"] is not None  # recurring schedule detected


def test_parse_freetext_guardian_marker():
    raw = "Liam Nguyen, parent: Mai Nguyen, 0433 222 111"
    out = svc.parse_text(raw)
    c = out["candidates"][0]
    assert c["name"] == "Liam Nguyen"
    assert c["guardians"][0]["name"].startswith("Mai")


def test_missing_name_lowers_confidence():
    out = svc.parse_text("ada@x.com,0400000000")
    c = out["candidates"][0]
    assert c["confidence"] < 1.0
    assert any("name" in w.lower() for w in c["warnings"])


# --- endpoint: parse -> review -> commit ------------------------------------
def test_parse_endpoint_creates_review_job_without_writing_students(client):
    h = _auth(client)
    raw = "Name,Email\nAda,ada@x.com\nGrace,grace@navy.mil"
    r = client.post("/api/v1/students/import/parse", json={"rawInput": raw}, headers=h)
    assert r.status_code == 201, r.text
    job = r.json()
    assert job["status"] == "review"
    assert len(job["parsed"]["candidates"]) == 2

    # Nothing written yet — confirm gate.
    assert client.get("/api/v1/students", headers=h).json()["items"] == []


def test_commit_creates_students_and_guardians(client):
    h = _auth(client)
    raw = "Student Name,Guardian,Parent Phone\nTommy,Jane,0400999888"
    job = client.post(
        "/api/v1/students/import/parse", json={"rawInput": raw}, headers=h
    ).json()

    commit = client.post(
        f"/api/v1/students/import/{job['id']}/commit",
        json={"parsed": job["parsed"]},
        headers=h,
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["status"] == "committed"
    assert len(commit.json()["parsed"]["createdStudentIds"]) == 1

    students = client.get("/api/v1/students", headers=h).json()["items"]
    assert [s["name"] for s in students] == ["Tommy"]
    guardians = client.get(
        f"/api/v1/guardians?studentId={students[0]['id']}", headers=h
    ).json()["items"]
    assert guardians[0]["name"] == "Jane"


def test_commit_uses_edited_structure(client):
    h = _auth(client)
    job = client.post(
        "/api/v1/students/import/parse",
        json={"rawInput": "Name\nOriginal"},
        headers=h,
    ).json()
    edited = {
        "candidates": [
            {
                "name": "Edited Name",
                "email": "edit@x.com",
                "status": "paused",
                "tags": ["vce"],
            },
            {"name": "", "skip": True},  # skipped row
        ]
    }
    commit = client.post(
        f"/api/v1/students/import/{job['id']}/commit",
        json={"parsed": edited},
        headers=h,
    )
    assert commit.status_code == 200, commit.text
    students = client.get("/api/v1/students", headers=h).json()["items"]
    assert len(students) == 1
    assert students[0]["name"] == "Edited Name"
    assert students[0]["status"] == "paused"


def test_double_commit_rejected(client):
    h = _auth(client)
    job = client.post(
        "/api/v1/students/import/parse",
        json={"rawInput": "Name\nA"},
        headers=h,
    ).json()
    payload = {"parsed": job["parsed"]}
    assert client.post(
        f"/api/v1/students/import/{job['id']}/commit", json=payload, headers=h
    ).status_code == 200
    again = client.post(
        f"/api/v1/students/import/{job['id']}/commit", json=payload, headers=h
    )
    assert again.status_code == 409


def test_import_job_is_org_scoped(client):
    a = _auth(client, email="a@example.com", org="A")
    b = _auth(client, email="b@example.com", org="B")
    job = client.post(
        "/api/v1/students/import/parse", json={"rawInput": "Name\nA"}, headers=a
    ).json()
    r = client.get(f"/api/v1/students/import/{job['id']}", headers=b)
    assert r.status_code == 404
