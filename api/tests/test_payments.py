"""Payments tests (CO-P01): record payments + this-month income overview."""
from __future__ import annotations

import uuid

from app.models.student import Student


def _register(client, email="owner@example.com"):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "name": "Owner",
            "orgName": "Acme Tutoring",
        },
    )
    assert r.status_code == 201, r.text
    headers = {"Authorization": f"Bearer {r.json()['token']}"}
    org_id = uuid.UUID(r.json()["user"]["orgId"])
    return headers, org_id


def _make_student(db, org_id, name="Kid"):
    s = Student(org_id=org_id, name=name)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s.id


def test_record_and_list_payment(client, db):
    headers, org_id = _register(client)
    student_id = _make_student(db, org_id)

    r = client.post(
        "/api/v1/payments",
        headers=headers,
        json={
            "studentId": str(student_id),
            "amount": "120.00",
            "method": "cash",
            "note": "Term 1",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["amount"] == "120.00"
    assert body["method"] == "cash"
    assert body["status"] == "paid"

    rows = client.get("/api/v1/payments", headers=headers).json()["items"]
    assert len(rows) == 1
    assert rows[0]["studentId"] == str(student_id)


def test_revenue_overview_paid_vs_due(client, db):
    headers, org_id = _register(client)
    student_id = _make_student(db, org_id)

    # Two paid + one due, all in the current month (default paid_at = now).
    for amt in ("100.00", "50.00"):
        client.post(
            "/api/v1/payments",
            headers=headers,
            json={
                "studentId": str(student_id),
                "amount": amt,
                "method": "transfer",
            },
        )
    client.post(
        "/api/v1/payments",
        headers=headers,
        json={
            "studentId": str(student_id),
            "amount": "75.00",
            "method": "other",
            "status": "due",
        },
    )

    overview = client.get("/api/v1/payments/overview", headers=headers).json()
    assert overview["received"] == "150.00"
    assert overview["due"] == "75.00"


def test_record_payment_unknown_student(client):
    headers, _ = _register(client)
    r = client.post(
        "/api/v1/payments",
        headers=headers,
        json={
            "studentId": str(uuid.uuid4()),
            "amount": "10.00",
            "method": "cash",
        },
    )
    assert r.status_code == 404


def test_payments_cross_tenant_isolation(client, db):
    headers_a, org_a = _register(client, email="a@example.com")
    student_a = _make_student(db, org_a)
    client.post(
        "/api/v1/payments",
        headers=headers_a,
        json={"studentId": str(student_a), "amount": "99.00", "method": "cash"},
    )

    headers_b, _ = _register(client, email="b@example.com")
    rows = client.get("/api/v1/payments", headers=headers_b).json()["items"]
    assert rows == []  # org B sees none of org A's payments
