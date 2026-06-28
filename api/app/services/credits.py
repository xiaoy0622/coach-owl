"""Credits / lesson-pack ledger service (CO-K01).

The single source of truth for a student's balance is the **immutable**
``credit_ledger`` table: every purchase/deduct/refund/adjust appends one row and
``get_balance(student) == SUM(delta)``. We never store or mutate a running
balance number (§1.5 / §4 invariant 1).

Concurrency: ``deduct`` takes a row lock on the student row (``SELECT … FOR
UPDATE``) before reading the balance and appending the negative delta, so two
concurrent deducts on the same student are serialized and can never over-deduct
(§4 invariant — "no over-deduct").
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.credits import CreditLedger, CreditPack
from app.models.enums import LedgerReason
from app.models.student import Student
from app.schemas.credits import (
    CreditDeductRequest,
    CreditPackCreate,
    LedgerAdjustRequest,
)

# Default low-balance threshold (sessions). Configurable per call via the
# balance endpoint's ``threshold`` query param.
DEFAULT_LOW_BALANCE_THRESHOLD = 2


def _require_student(db: Session, org_id: uuid.UUID, student_id: uuid.UUID) -> Student:
    student = db.scalar(
        select(Student).where(
            Student.id == student_id, Student.org_id == org_id
        )
    )
    if student is None:
        raise AppError("Student not found", code="not_found", status_code=404)
    return student


def get_balance(db: Session, org_id: uuid.UUID, student_id: uuid.UUID) -> int:
    """Derived balance = SUM(ledger.delta) for the org-scoped student."""
    total = db.scalar(
        select(func.coalesce(func.sum(CreditLedger.delta), 0)).where(
            CreditLedger.org_id == org_id,
            CreditLedger.student_id == student_id,
        )
    )
    return int(total or 0)


def buy_pack(
    db: Session, org_id: uuid.UUID, body: CreditPackCreate
) -> CreditPack:
    """Create a pack and credit +total_sessions to the ledger (one transaction)."""
    _require_student(db, org_id, body.student_id)

    pack = CreditPack(
        org_id=org_id,
        student_id=body.student_id,
        name=body.name,
        total_sessions=body.total_sessions,
        price_per_session=body.price_per_session,
        expires_at=body.expires_at,
    )
    db.add(pack)
    db.flush()  # assign pack.id

    db.add(
        CreditLedger(
            org_id=org_id,
            student_id=body.student_id,
            pack_id=pack.id,
            delta=body.total_sessions,
            reason=LedgerReason.purchase,
        )
    )
    db.commit()
    db.refresh(pack)
    return pack


def list_packs(
    db: Session, org_id: uuid.UUID, student_id: uuid.UUID | None = None
) -> Sequence[CreditPack]:
    stmt = select(CreditPack).where(CreditPack.org_id == org_id)
    if student_id is not None:
        stmt = stmt.where(CreditPack.student_id == student_id)
    stmt = stmt.order_by(CreditPack.purchased_at.desc())
    return list(db.scalars(stmt))


def list_ledger(
    db: Session, org_id: uuid.UUID, student_id: uuid.UUID | None = None
) -> Sequence[CreditLedger]:
    stmt = select(CreditLedger).where(CreditLedger.org_id == org_id)
    if student_id is not None:
        stmt = stmt.where(CreditLedger.student_id == student_id)
    stmt = stmt.order_by(CreditLedger.created_at.desc())
    return list(db.scalars(stmt))


def adjust_ledger(
    db: Session, org_id: uuid.UUID, body: LedgerAdjustRequest
) -> CreditLedger:
    """Append a manual ledger entry (refund / adjust)."""
    if body.delta == 0:
        raise AppError(
            "delta must be non-zero", code="invalid_delta", status_code=400
        )
    _require_student(db, org_id, body.student_id)

    entry = CreditLedger(
        org_id=org_id,
        student_id=body.student_id,
        pack_id=body.pack_id,
        delta=body.delta,
        reason=body.reason,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def deduct(
    db: Session, org_id: uuid.UUID, body: CreditDeductRequest
) -> CreditLedger:
    """Deduct ``count`` credits, row-locking the student to prevent over-deduct.

    Locks the student row FOR UPDATE so any concurrent deduct on the same
    student blocks until this transaction commits; the balance is read *after*
    acquiring the lock, guaranteeing it can never go negative.
    """
    # Acquire the per-student lock (org-scoped). This serializes deducts.
    locked = db.scalar(
        select(Student.id)
        .where(Student.id == body.student_id, Student.org_id == org_id)
        .with_for_update()
    )
    if locked is None:
        raise AppError("Student not found", code="not_found", status_code=404)

    balance = get_balance(db, org_id, body.student_id)
    if balance < body.count:
        raise AppError(
            "Insufficient credit balance",
            code="insufficient_balance",
            status_code=409,
            details={"balance": balance, "requested": body.count},
        )

    entry = CreditLedger(
        org_id=org_id,
        student_id=body.student_id,
        lesson_id=body.lesson_id,
        delta=-body.count,
        reason=LedgerReason.deduct,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
