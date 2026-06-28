"""Read-only share links — management (org-scoped) + public resolve (CO-W06)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta


# --------------------------------------------------------------------------- #
# Helpers — build an org with a student, a future lesson and a credit balance  #
# via the real API (mirrors the public flow's data sources).                   #
# --------------------------------------------------------------------------- #
def _register(client, email="owner@example.com", org="Acme Tutoring"):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "name": "Owner One",
            "orgName": org,
        },
    )
    assert r.status_code == 201, r.text
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/v1/auth/me", headers=headers).json()
    return headers, me["user"]["id"]


def _create_student(client, headers, name="Tommy Smith"):
    r = client.post("/api/v1/students", headers=headers, json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _create_lesson(client, headers, student_id, coach_id, *, starts_at, duration=60):
    r = client.post(
        "/api/v1/lessons",
        headers=headers,
        json={
            "studentId": student_id,
            "coachId": coach_id,
            "startsAt": starts_at,
            "durationMin": duration,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["items"][0]


def _buy_pack(client, headers, student_id, sessions=10):
    r = client.post(
        "/api/v1/credits/packs",
        headers=headers,
        json={
            "studentId": student_id,
            "name": "Term pack",
            "totalSessions": sessions,
            "pricePerSession": "50.00",
        },
    )
    assert r.status_code == 201, r.text


def _future_iso(days=7):
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


# --------------------------------------------------------------------------- #
# Management endpoints (org-scoped, Bearer)                                     #
# --------------------------------------------------------------------------- #
def test_create_list_revoke_share_link(client):
    headers, _ = _register(client)
    student_id = _create_student(client, headers)

    # Create.
    r = client.post(
        "/api/v1/share-links", headers=headers, json={"studentId": student_id}
    )
    assert r.status_code == 201, r.text
    link = r.json()
    assert link["studentId"] == student_id
    assert link["token"]
    assert len(link["token"]) >= 20  # secure random token
    assert link["orgId"]  # camelCase
    link_id = link["id"]

    # List (org-scoped) — and filtered by student.
    r = client.get("/api/v1/share-links", headers=headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1 and items[0]["id"] == link_id

    r = client.get(
        f"/api/v1/share-links?studentId={student_id}", headers=headers
    )
    assert len(r.json()["items"]) == 1

    # Revoke → 204, then gone from the list and the token stops resolving.
    token = link["token"]
    r = client.delete(f"/api/v1/share-links/{link_id}", headers=headers)
    assert r.status_code == 204, r.text
    assert client.get("/api/v1/share-links", headers=headers).json()["items"] == []

    r = client.get(f"/api/v1/share-links/public/{token}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_create_requires_auth(client):
    r = client.post(
        "/api/v1/share-links", json={"studentId": str(uuid.uuid4())}
    )
    assert r.status_code == 401


def test_create_unknown_student_rejected(client):
    headers, _ = _register(client)
    r = client.post(
        "/api/v1/share-links",
        headers=headers,
        json={"studentId": str(uuid.uuid4())},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


# --------------------------------------------------------------------------- #
# Public resolve (no auth) — only that student's schedule + balance            #
# --------------------------------------------------------------------------- #
def test_public_resolve_returns_only_that_student(client):
    headers, coach_id = _register(client)
    alice = _create_student(client, headers, name="Alice")
    bob = _create_student(client, headers, name="Bob")

    # Alice: a credit pack + a future lesson; Bob: his own future lesson.
    _buy_pack(client, headers, alice, sessions=8)
    alice_lesson = _create_lesson(
        client, headers, alice, coach_id, starts_at=_future_iso(3)
    )
    _create_lesson(client, headers, bob, coach_id, starts_at=_future_iso(4))

    r = client.post(
        "/api/v1/share-links", headers=headers, json={"studentId": alice}
    )
    token = r.json()["token"]

    # PUBLIC call: no Authorization header.
    r = client.get(f"/api/v1/share-links/public/{token}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["studentName"] == "Alice"
    assert data["creditBalance"] == 8
    assert data["timezone"] == "Australia/Sydney"
    assert len(data["upcomingLessons"]) == 1
    lesson = data["upcomingLessons"][0]
    assert lesson["startsAt"] == alice_lesson["startsAt"]
    assert lesson["durationMin"] == 60
    # No leak of Bob's data or any other student's fields.
    assert "studentId" not in lesson and "id" not in lesson
    assert "Bob" not in r.text


def test_public_resolve_invalid_token_404(client):
    r = client.get("/api/v1/share-links/public/not-a-real-token")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_public_resolve_expired_token_410(client):
    headers, _ = _register(client)
    student_id = _create_student(client, headers)
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()

    r = client.post(
        "/api/v1/share-links",
        headers=headers,
        json={"studentId": student_id, "expiresAt": past},
    )
    token = r.json()["token"]

    r = client.get(f"/api/v1/share-links/public/{token}")
    assert r.status_code == 410
    assert r.json()["error"]["code"] == "expired"


def test_public_resolve_omits_non_scheduled_and_past(client):
    headers, coach_id = _register(client)
    student_id = _create_student(client, headers)
    # A future lesson then cancel it → should NOT appear as upcoming.
    lesson = _create_lesson(
        client, headers, student_id, coach_id, starts_at=_future_iso(5)
    )
    r = client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        headers=headers,
        json={"status": "cancelled", "cancelReason": "sick"},
    )
    assert r.status_code == 200, r.text

    r = client.post(
        "/api/v1/share-links", headers=headers, json={"studentId": student_id}
    )
    token = r.json()["token"]

    data = client.get(f"/api/v1/share-links/public/{token}").json()
    assert data["upcomingLessons"] == []
    assert data["creditBalance"] == 0


# --------------------------------------------------------------------------- #
# Cross-org isolation                                                          #
# --------------------------------------------------------------------------- #
def test_org_b_cannot_manage_org_a_link(client):
    headers_a, _ = _register(client, email="a@example.com", org="Org A")
    headers_b, _ = _register(client, email="b@example.com", org="Org B")
    student_a = _create_student(client, headers_a, name="A-student")

    r = client.post(
        "/api/v1/share-links", headers=headers_a, json={"studentId": student_a}
    )
    link_a = r.json()

    # Org B cannot see Org A's links.
    assert client.get("/api/v1/share-links", headers=headers_b).json()["items"] == []

    # Org B cannot revoke Org A's link (scoped 404, and it still resolves).
    r = client.delete(f"/api/v1/share-links/{link_a['id']}", headers=headers_b)
    assert r.status_code == 404
    assert (
        client.get(f"/api/v1/share-links/public/{link_a['token']}").status_code
        == 200
    )

    # Org B cannot create a link for Org A's student.
    r = client.post(
        "/api/v1/share-links", headers=headers_b, json={"studentId": student_a}
    )
    assert r.status_code == 404
