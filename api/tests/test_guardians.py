"""Guardians: multiple per student, is_primary, minor-must-keep-primary (CO-S02)."""
from __future__ import annotations


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


def _student(client, h, **kw):
    body = {"name": "Kid Student", **kw}
    return client.post("/api/v1/students", json=body, headers=h).json()


def test_attach_multiple_guardians(client):
    h = _auth(client)
    s = _student(client, h)
    g1 = client.post(
        "/api/v1/guardians",
        json={
            "studentId": s["id"],
            "name": "Mum",
            "isPrimary": True,
            "relationship": "mother",
        },
        headers=h,
    )
    assert g1.status_code == 201, g1.text
    assert g1.json()["isPrimary"] is True
    client.post(
        "/api/v1/guardians",
        json={"studentId": s["id"], "name": "Dad", "isPrimary": False},
        headers=h,
    )

    listed = client.get(f"/api/v1/guardians?studentId={s['id']}", headers=h).json()
    assert {g["name"] for g in listed["items"]} == {"Mum", "Dad"}
    # Primary sorts first.
    assert listed["items"][0]["name"] == "Mum"


def test_create_guardian_rejects_foreign_student(client):
    a = _auth(client, email="a@example.com", org="A")
    b = _auth(client, email="b@example.com", org="B")
    s = _student(client, a)
    r = client.post(
        "/api/v1/guardians",
        json={"studentId": s["id"], "name": "X"},
        headers=b,
    )
    assert r.status_code == 404


def test_minor_must_keep_primary_guardian_on_delete(client):
    h = _auth(client)
    s = _student(client, h, tags=["minor"])
    g = client.post(
        "/api/v1/guardians",
        json={"studentId": s["id"], "name": "Sole Parent", "isPrimary": True},
        headers=h,
    ).json()

    # Deleting the only primary guardian of a minor is rejected.
    r = client.delete(f"/api/v1/guardians/{g['id']}", headers=h)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "primary_guardian_required"

    # Demoting it is likewise rejected.
    r = client.patch(
        f"/api/v1/guardians/{g['id']}", json={"isPrimary": False}, headers=h
    )
    assert r.status_code == 422


def test_minor_with_two_primaries_can_remove_one(client):
    h = _auth(client)
    s = _student(client, h, tags=["minor"])
    g1 = client.post(
        "/api/v1/guardians",
        json={"studentId": s["id"], "name": "P1", "isPrimary": True},
        headers=h,
    ).json()
    client.post(
        "/api/v1/guardians",
        json={"studentId": s["id"], "name": "P2", "isPrimary": True},
        headers=h,
    )
    assert client.delete(f"/api/v1/guardians/{g1['id']}", headers=h).status_code == 204


def test_non_minor_primary_can_be_removed(client):
    h = _auth(client)
    s = _student(client, h)  # no "minor" tag
    g = client.post(
        "/api/v1/guardians",
        json={"studentId": s["id"], "name": "Only", "isPrimary": True},
        headers=h,
    ).json()
    assert client.delete(f"/api/v1/guardians/{g['id']}", headers=h).status_code == 204
