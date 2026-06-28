"""Payment contracts + revenue overview (CO-P01)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import PaymentMethod, PaymentStatus
from app.schemas.common import CamelModel, Money


class PaymentBase(CamelModel):
    student_id: uuid.UUID
    amount: Money
    method: PaymentMethod
    pack_id: uuid.UUID | None = None
    note: str | None = None
    status: PaymentStatus = PaymentStatus.paid


class PaymentCreate(PaymentBase):
    paid_at: datetime | None = None


class PaymentOut(PaymentBase):
    id: uuid.UUID
    org_id: uuid.UUID
    paid_at: datetime
    created_at: datetime


class RevenueOverview(CamelModel):
    """This-month aggregates (§flow C: received vs due)."""

    period_start: datetime
    period_end: datetime
    received: Money = Field(default=0)
    due: Money = Field(default=0)
