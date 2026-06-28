"""Cross-tenant isolation: a user from org A cannot see org B's data."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.deps import scoped
from app.core.security import decode_access_token
from app.models.student import Student


def _register(client, email, org):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "name": "U", "orgName": org},
    ).json()


def test_scoped_helper_filters_by_org(client, db):
    a = _register(client, "a@example.com", "Org A")
    b = _register(client, "b@example.com", "Org B")
    org_a = uuid.UUID(a["user"]["orgId"])
    org_b = uuid.UUID(b["user"]["orgId"])
    assert org_a != org_b

    db.add(Student(org_id=org_a, name="Alice (A)"))
    db.add(Student(org_id=org_a, name="Avery (A)"))
    db.add(Student(org_id=org_b, name="Bob (B)"))
    db.commit()

    a_students = db.scalars(scoped(select(Student), org_a, Student)).all()
    b_students = db.scalars(scoped(select(Student), org_b, Student)).all()

    assert {s.name for s in a_students} == {"Alice (A)", "Avery (A)"}
    assert {s.name for s in b_students} == {"Bob (B)"}
    # Org A's scoped query never leaks Org B rows.
    assert all(s.org_id == org_a for s in a_students)


def test_token_org_matches_user_org(client):
    a = _register(client, "a@example.com", "Org A")
    claims = decode_access_token(a["token"])
    assert claims["org_id"] == a["user"]["orgId"]
    assert claims["sub"] == a["user"]["id"]


def test_me_returns_own_org_only(client):
    _register(client, "a@example.com", "Org A")
    b = _register(client, "b@example.com", "Org B")
    me_b = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {b['token']}"},
    ).json()
    assert me_b["org"]["name"] == "Org B"
