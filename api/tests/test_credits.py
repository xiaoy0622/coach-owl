"""Credits / ledger tests (CO-K01).

Asserts the §4 invariants: balance == SUM(ledger.delta), and concurrent deducts
can never over-deduct (row locking serializes them).
"""
from __future__ import annotations

import threading
import uuid

from app.models.organization import Organization
from app.models.student import Student
from app.schemas.credits import CreditDeductRequest
from app.services import credits as credits_service


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
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    org_id = uuid.UUID(r.json()["user"]["orgId"])
    return headers, org_id


def _make_student(db, org_id, name="Kid"):
    s = Student(org_id=org_id, name=name)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s.id


def test_buy_pack_credits_ledger_and_balance(client, db):
    headers, org_id = _register(client)
    student_id = _make_student(db, org_id)

    r = client.post(
        "/api/v1/credits/packs",
        headers=headers,
        json={
            "studentId": str(student_id),
            "name": "10-pack",
            "totalSessions": 10,
            "pricePerSession": "50.00",
        },
    )
    assert r.status_code == 201, r.text

    # Balance reflects the +10 purchase entry.
    b = client.get(
        f"/api/v1/credits/balance/{student_id}", headers=headers
    ).json()
    assert b["balance"] == 10

    # Ledger has exactly one purchase entry of +10.
    ledger = client.get(
        f"/api/v1/credits/ledger?studentId={student_id}", headers=headers
    ).json()["items"]
    assert len(ledger) == 1
    assert ledger[0]["delta"] == 10
    assert ledger[0]["reason"] == "purchase"


def test_balance_equals_sum_of_deltas(client, db):
    """§4 invariant 1: balance == SUM(delta)."""
    headers, org_id = _register(client)
    student_id = _make_student(db, org_id)

    client.post(
        "/api/v1/credits/packs",
        headers=headers,
        json={
            "studentId": str(student_id),
            "name": "10-pack",
            "totalSessions": 10,
            "pricePerSession": "50.00",
        },
    )
    # Two deducts and a manual -1 adjustment.
    for _ in range(2):
        assert (
            client.post(
                "/api/v1/credits/deduct",
                headers=headers,
                json={"studentId": str(student_id)},
            ).status_code
            == 201
        )
    client.post(
        "/api/v1/credits/ledger",
        headers=headers,
        json={"studentId": str(student_id), "delta": -1, "reason": "adjust"},
    )

    ledger = client.get(
        f"/api/v1/credits/ledger?studentId={student_id}", headers=headers
    ).json()["items"]
    summed = sum(e["delta"] for e in ledger)
    balance = client.get(
        f"/api/v1/credits/balance/{student_id}", headers=headers
    ).json()["balance"]
    assert balance == summed == 7


def test_deduct_blocks_overdeduct(client, db):
    headers, org_id = _register(client)
    student_id = _make_student(db, org_id)

    client.post(
        "/api/v1/credits/packs",
        headers=headers,
        json={
            "studentId": str(student_id),
            "name": "single",
            "totalSessions": 1,
            "pricePerSession": "50.00",
        },
    )
    # First deduct succeeds (balance -> 0).
    assert (
        client.post(
            "/api/v1/credits/deduct",
            headers=headers,
            json={"studentId": str(student_id)},
        ).status_code
        == 201
    )
    # Second deduct is rejected — no over-deduct.
    r = client.post(
        "/api/v1/credits/deduct",
        headers=headers,
        json={"studentId": str(student_id)},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "insufficient_balance"
    assert (
        client.get(
            f"/api/v1/credits/balance/{student_id}", headers=headers
        ).json()["balance"]
        == 0
    )


def test_concurrent_deduct_no_overdeduct(session_factory):
    """Two simultaneous deducts on a 1-credit student → exactly one wins."""
    # Seed an org + student + a single credit, directly.
    setup = session_factory()
    org = Organization(name="Acme")
    setup.add(org)
    setup.flush()
    org_id = org.id
    student = Student(org_id=org_id, name="Kid")
    setup.add(student)
    setup.flush()
    student_id = student.id
    from app.models.credits import CreditLedger
    from app.models.enums import LedgerReason

    setup.add(
        CreditLedger(
            org_id=org_id,
            student_id=student_id,
            delta=1,
            reason=LedgerReason.purchase,
        )
    )
    setup.commit()
    setup.close()

    barrier = threading.Barrier(2)
    results: list[str] = []
    lock = threading.Lock()

    def worker():
        s = session_factory()
        try:
            barrier.wait()
            credits_service.deduct(
                s, org_id, CreditDeductRequest(student_id=student_id)
            )
            with lock:
                results.append("ok")
        except Exception as exc:  # noqa: BLE001
            with lock:
                results.append(type(exc).__name__)
        finally:
            s.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count("ok") == 1, results

    verify = session_factory()
    try:
        bal = credits_service.get_balance(verify, org_id, student_id)
        assert bal == 0  # never went negative
    finally:
        verify.close()


def test_adjust_refund(client, db):
    headers, org_id = _register(client)
    student_id = _make_student(db, org_id)

    r = client.post(
        "/api/v1/credits/ledger",
        headers=headers,
        json={"studentId": str(student_id), "delta": 3, "reason": "refund"},
    )
    assert r.status_code == 201
    assert r.json()["reason"] == "refund"
    assert (
        client.get(
            f"/api/v1/credits/balance/{student_id}", headers=headers
        ).json()["balance"]
        == 3
    )


def test_low_balance_flag(client, db):
    headers, org_id = _register(client)
    student_id = _make_student(db, org_id)
    client.post(
        "/api/v1/credits/ledger",
        headers=headers,
        json={"studentId": str(student_id), "delta": 1, "reason": "adjust"},
    )
    # threshold=2 (default) -> balance 1 is low.
    b = client.get(
        f"/api/v1/credits/balance/{student_id}", headers=headers
    ).json()
    assert b["lowBalance"] is True
    assert b["threshold"] == 2
    # Override threshold to 0 -> not low.
    b2 = client.get(
        f"/api/v1/credits/balance/{student_id}?threshold=0", headers=headers
    ).json()
    assert b2["lowBalance"] is False


def test_buy_pack_cross_tenant_rejected(client, db):
    # Student belongs to org A; org B (different login) cannot buy them a pack.
    headers_a, org_a = _register(client, email="a@example.com")
    student_id = _make_student(db, org_a)
    headers_b, _ = _register(client, email="b@example.com")

    r = client.post(
        "/api/v1/credits/packs",
        headers=headers_b,
        json={
            "studentId": str(student_id),
            "name": "10-pack",
            "totalSessions": 10,
            "pricePerSession": "50.00",
        },
    )
    assert r.status_code == 404
