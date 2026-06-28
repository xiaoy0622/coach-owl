"""Auth happy path + org onboarding (CO-F03)."""
from __future__ import annotations


def _register(client, email="owner@example.com", password="supersecret1", **kw):
    body = {"email": email, "password": password, "name": "Owner One", **kw}
    return client.post("/api/v1/auth/register", json=body)


def test_register_login_me_happy_path(client):
    # Register -> 201 with token + camelCase user.
    r = _register(client, orgName="Acme Tutoring")
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["token"]
    user = data["user"]
    assert user["email"] == "owner@example.com"
    assert user["role"] == "owner"
    assert user["orgId"]  # camelCase

    # Login -> 200 with a token.
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "supersecret1"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["token"]

    # /me -> user + org with AU defaults.
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["user"]["email"] == "owner@example.com"
    org = me["org"]
    assert org["name"] == "Acme Tutoring"
    assert org["timezone"] == "Australia/Sydney"
    assert org["currency"] == "AUD"
    assert org["gstEnabled"] is False
    assert org["gstRate"] == "0.1000"


def test_register_default_org_name(client):
    r = _register(client, email="solo@example.com")
    assert r.status_code == 201
    token = r.json()["token"]
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert me["org"]["name"] == "Owner One's Studio"


def test_duplicate_email_rejected(client):
    assert _register(client).status_code == 201
    r = _register(client)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


def test_login_wrong_password(client):
    _register(client)
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "wrongpassword"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_credentials"


def test_me_requires_token(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_owner_can_update_org(client):
    token = _register(client).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.patch(
        "/api/v1/org",
        headers=headers,
        json={"gstEnabled": True, "timezone": "Australia/Perth", "abn": "12345678901"},
    )
    assert r.status_code == 200, r.text
    org = r.json()
    assert org["gstEnabled"] is True
    assert org["timezone"] == "Australia/Perth"
    assert org["abn"] == "12345678901"
