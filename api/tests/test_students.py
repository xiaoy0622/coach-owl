"""Student CRUD, search, pagination + tenant isolation (CO-S01)."""
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
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _create(client, headers, **kw):
    body = {"name": "Ada Lovelace", **kw}
    return client.post("/api/v1/students", json=body, headers=headers)


def test_create_and_get_student(client):
    h = _auth(client)
    r = _create(client, h, email="ada@example.com", phone="0400000000", tags=["math"])
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["name"] == "Ada Lovelace"
    assert s["email"] == "ada@example.com"
    assert s["status"] == "active"
    assert s["tags"] == ["math"]
    assert s["orgId"]  # camelCase

    got = client.get(f"/api/v1/students/{s['id']}", headers=h)
    assert got.status_code == 200
    assert got.json()["id"] == s["id"]


def test_update_and_delete_student(client):
    h = _auth(client)
    s = _create(client, h).json()
    r = client.patch(
        f"/api/v1/students/{s['id']}",
        json={"status": "paused", "tags": ["english", "english"]},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "paused"
    assert r.json()["tags"] == ["english"]  # de-duped

    d = client.delete(f"/api/v1/students/{s['id']}", headers=h)
    assert d.status_code == 204
    assert client.get(f"/api/v1/students/{s['id']}", headers=h).status_code == 404


def test_list_search_and_status_filter(client):
    h = _auth(client)
    _create(client, h, name="Grace Hopper", email="grace@navy.mil")
    _create(client, h, name="Ada Byron", status="churned")
    _create(client, h, name="Alan Turing")

    r = client.get("/api/v1/students?search=grace", headers=h)
    assert r.status_code == 200
    names = [i["name"] for i in r.json()["items"]]
    assert names == ["Grace Hopper"]

    r = client.get("/api/v1/students?status=churned", headers=h)
    assert [i["name"] for i in r.json()["items"]] == ["Ada Byron"]


def test_tag_filter(client):
    h = _auth(client)
    _create(client, h, name="A", tags=["vce", "math"])
    _create(client, h, name="B", tags=["primary"])
    r = client.get("/api/v1/students?tag=vce", headers=h)
    assert [i["name"] for i in r.json()["items"]] == ["A"]


def test_cursor_pagination(client):
    h = _auth(client)
    for i in range(5):
        _create(client, h, name=f"S{i}")

    r = client.get("/api/v1/students?limit=2", headers=h)
    body = r.json()
    assert len(body["items"]) == 2
    assert body["nextCursor"]

    seen = [i["name"] for i in body["items"]]
    cursor = body["nextCursor"]
    while cursor:
        r = client.get(f"/api/v1/students?limit=2&cursor={cursor}", headers=h)
        body = r.json()
        seen += [i["name"] for i in body["items"]]
        cursor = body["nextCursor"]
    assert seen == ["S0", "S1", "S2", "S3", "S4"]  # stable order, no dupes


def test_students_are_org_scoped(client):
    a = _auth(client, email="a@example.com", org="Org A")
    b = _auth(client, email="b@example.com", org="Org B")
    s = _create(client, a, name="A-only").json()

    # Org B cannot see or fetch Org A's student.
    assert client.get("/api/v1/students", headers=b).json()["items"] == []
    assert client.get(f"/api/v1/students/{s['id']}", headers=b).status_code == 404
    assert client.delete(f"/api/v1/students/{s['id']}", headers=b).status_code == 404


def test_list_requires_auth(client):
    assert client.get("/api/v1/students").status_code == 401
