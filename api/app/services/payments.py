"""Payments service: record payments + this-month income overview (CO-P01).

Income overview reports *paid vs outstanding (due)* for the current month, with
month boundaries computed in the org's timezone (AU localization) and converted
to UTC for the query. Everything is org-scoped.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.billing import Payment
from app.models.enums import PaymentStatus
from app.models.organization import Organization
from app.models.student import Student
from app.schemas.payments import PaymentCreate, RevenueOverview
from app.utils.localization import now_utc, round_money


def _require_student(db: Session, org_id: uuid.UUID, student_id: uuid.UUID) -> None:
    exists = db.scalar(
        select(Student.id).where(
            Student.id == student_id, Student.org_id == org_id
        )
    )
    if exists is None:
        raise AppError("Student not found", code="not_found", status_code=404)


def record_payment(
    db: Session, org_id: uuid.UUID, body: PaymentCreate
) -> Payment:
    _require_student(db, org_id, body.student_id)

    payment = Payment(
        org_id=org_id,
        student_id=body.student_id,
        amount=body.amount,
        method=body.method,
        pack_id=body.pack_id,
        note=body.note,
        status=body.status,
    )
    if body.paid_at is not None:
        payment.paid_at = body.paid_at
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def list_payments(db: Session, org_id: uuid.UUID) -> Sequence[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.org_id == org_id)
        .order_by(Payment.paid_at.desc())
    )
    return list(db.scalars(stmt))


def _month_bounds_utc(tz_name: str, *, at: datetime) -> tuple[datetime, datetime]:
    """Return [start, end) of ``at``'s month, in org tz, as UTC datetimes."""
    tz = ZoneInfo(tz_name)
    local = at.astimezone(tz)
    start_local = local.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    if start_local.month == 12:
        end_local = start_local.replace(year=start_local.year + 1, month=1)
    else:
        end_local = start_local.replace(month=start_local.month + 1)
    return start_local.astimezone(ZoneInfo("UTC")), end_local.astimezone(
        ZoneInfo("UTC")
    )


def revenue_overview(
    db: Session,
    org_id: uuid.UUID,
    *,
    at: datetime | None = None,
) -> RevenueOverview:
    """This-month received (status=paid) vs due (status=due), org-scoped."""
    org = db.get(Organization, org_id)
    tz_name = org.timezone if org is not None else "Australia/Sydney"
    at = at or now_utc()
    start, end = _month_bounds_utc(tz_name, at=at)

    def _sum(status: PaymentStatus) -> Decimal:
        total = db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.org_id == org_id,
                Payment.status == status,
                Payment.paid_at >= start,
                Payment.paid_at < end,
            )
        )
        return round_money(total or 0)

    return RevenueOverview(
        period_start=start,
        period_end=end,
        received=_sum(PaymentStatus.paid),
        due=_sum(PaymentStatus.due),
    )
