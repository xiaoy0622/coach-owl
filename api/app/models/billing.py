"""Payments and invoices."""
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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, OrgScopedMixin
from app.models._types import str_enum
from app.models.enums import InvoiceStatus, PaymentMethod, PaymentStatus


class Payment(OrgScopedMixin, Base):
    __tablename__ = "payments"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        str_enum(PaymentMethod, "payment_method"), nullable=False
    )
    pack_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("credit_packs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(
        str_enum(PaymentStatus, "payment_status"),
        nullable=False,
        default=PaymentStatus.paid,
    )


class Invoice(OrgScopedMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("org_id", "number", name="uq_invoices_org_number"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    line_items: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    gst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        str_enum(InvoiceStatus, "invoice_status"),
        nullable=False,
        default=InvoiceStatus.draft,
    )
    pdf_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
