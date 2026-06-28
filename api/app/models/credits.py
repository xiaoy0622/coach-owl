"""Credit packs and the immutable credit ledger (balance = SUM(delta))."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, OrgScopedMixin
from app.models._types import str_enum
from app.models.enums import LedgerReason


class CreditPack(OrgScopedMixin, Base):
    __tablename__ = "credit_packs"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_session: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CreditLedger(OrgScopedMixin, Base):
    """Append-only ledger. NEVER mutate rows; balance is derived."""

    __tablename__ = "credit_ledger"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pack_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("credit_packs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[LedgerReason] = mapped_column(
        str_enum(LedgerReason, "ledger_reason"), nullable=False
    )
