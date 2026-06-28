"""Organization (tenant root)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Australia/Sydney"
    )
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="AUD"
    )
    gst_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    gst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.10")
    )
    abn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    brand_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
