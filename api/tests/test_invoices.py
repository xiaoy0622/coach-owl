"""Invoice tests (CO-P02): GST on/off totals, org-sequential numbers, PDF."""
from __future__ import annotations

import uuid

from app.models.student import Student


def _register(client, email="owner@example.com", gst=False):
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
    if gst:
        client.patch(
            "/api/v1/org",
            headers=headers,
            json={"gstEnabled": True, "abn": "12345678901"},
        )
    return headers, org_id


def _make_student(db, org_id, name="Kid"):
    s = Student(org_id=org_id, name=name)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s.id


def _invoice_body(student_id):
    return {
        "studentId": str(student_id),
        "lineItems": [
            {
                "description": "4 x lessons",
                "quantity": 4,
                "unitPrice": "25.00",
                "amount": "100.00",
            }
        ],
    }


def test_invoice_gst_disabled(client, db):
    headers, org_id = _register(client, gst=False)
    student_id = _make_student(db, org_id)

    r = client.post(
        "/api/v1/invoices", headers=headers, json=_invoice_body(student_id)
    )
    assert r.status_code == 201, r.text
    inv = r.json()
    assert inv["subtotal"] == "100.00"
    assert inv["gstAmount"] == "0.00"
    assert inv["total"] == "100.00"
    assert inv["number"] == 1


def test_invoice_gst_enabled(client, db):
    headers, org_id = _register(client, gst=True)
    student_id = _make_student(db, org_id)

    r = client.post(
        "/api/v1/invoices", headers=headers, json=_invoice_body(student_id)
    )
    assert r.status_code == 201, r.text
    inv = r.json()
    assert inv["subtotal"] == "100.00"
    assert inv["gstAmount"] == "10.00"
    assert inv["total"] == "110.00"


def test_invoice_numbers_sequential_per_org(client, db):
    headers, org_id = _register(client)
    student_id = _make_student(db, org_id)

    numbers = []
    for _ in range(3):
        r = client.post(
            "/api/v1/invoices", headers=headers, json=_invoice_body(student_id)
        )
        numbers.append(r.json()["number"])
    assert numbers == [1, 2, 3]


def test_invoice_pdf_download(client, db):
    headers, org_id = _register(client, gst=True)
    student_id = _make_student(db, org_id)
    inv = client.post(
        "/api/v1/invoices", headers=headers, json=_invoice_body(student_id)
    ).json()

    assert inv["pdfUrl"] == f"/api/v1/invoices/{inv['id']}/pdf"
    r = client.get(f"/api/v1/invoices/{inv['id']}/pdf", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"


def test_invoice_get_and_list(client, db):
    headers, org_id = _register(client)
    student_id = _make_student(db, org_id)
    inv = client.post(
        "/api/v1/invoices", headers=headers, json=_invoice_body(student_id)
    ).json()

    got = client.get(f"/api/v1/invoices/{inv['id']}", headers=headers)
    assert got.status_code == 200
    assert got.json()["id"] == inv["id"]

    listed = client.get("/api/v1/invoices", headers=headers).json()["items"]
    assert len(listed) == 1


def test_invoice_cross_tenant_isolation(client, db):
    headers_a, org_a = _register(client, email="a@example.com")
    student_a = _make_student(db, org_a)
    inv = client.post(
        "/api/v1/invoices", headers=headers_a, json=_invoice_body(student_a)
    ).json()

    headers_b, _ = _register(client, email="b@example.com")
    # Org B cannot fetch org A's invoice or its PDF.
    assert (
        client.get(f"/api/v1/invoices/{inv['id']}", headers=headers_b).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/invoices/{inv['id']}/pdf", headers=headers_b
        ).status_code
        == 404
    )
