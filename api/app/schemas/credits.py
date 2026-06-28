"""Credits contracts: packs, ledger entries, balance (CO-K01)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import LedgerReason
from app.schemas.common import CamelModel, Money


class CreditPackBase(CamelModel):
    student_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    total_sessions: int = Field(gt=0)
    price_per_session: Money
    expires_at: datetime | None = None


class CreditPackCreate(CreditPackBase):
    pass


class CreditPackOut(CreditPackBase):
    id: uuid.UUID
    org_id: uuid.UUID
    purchased_at: datetime
    created_at: datetime


class LedgerEntryOut(CamelModel):
    id: uuid.UUID
    org_id: uuid.UUID
    student_id: uuid.UUID
    pack_id: uuid.UUID | None = None
    lesson_id: uuid.UUID | None = None
    delta: int
    reason: LedgerReason
    created_at: datetime


class LedgerAdjustRequest(CamelModel):
    """Manual ledger adjustment (refund/adjust); deduct/purchase happen via flows."""

    student_id: uuid.UUID
    delta: int
    reason: LedgerReason = LedgerReason.adjust
    pack_id: uuid.UUID | None = None


class CreditDeductRequest(CamelModel):
    """Deduct credit(s) when a lesson is consumed.

    Goes through row-locking so concurrent deducts can never over-deduct
    (§4 invariant). ``count`` is the number of credits to remove (default 1).
    """

    student_id: uuid.UUID
    lesson_id: uuid.UUID | None = None
    count: int = Field(default=1, gt=0)


class BalanceOut(CamelModel):
    student_id: uuid.UUID
    balance: int
    # Configurable low-balance threshold + a derived flag for the UI (CO-K01).
    threshold: int = 0
    low_balance: bool = False
