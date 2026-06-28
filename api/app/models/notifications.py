"""Notifications outbox (channel-agnostic). dedupe_key guarantees no resend."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, OrgScopedMixin
from app.models._types import str_enum
from app.models.enums import NotificationChannel, NotificationStatus


class Notification(OrgScopedMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_notifications_dedupe_key"),
    )

    channel: Mapped[NotificationChannel] = mapped_column(
        str_enum(NotificationChannel, "notification_channel"),
        nullable=False,
        default=NotificationChannel.email,
    )
    template: Mapped[str] = mapped_column(String(128), nullable=False)
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        str_enum(NotificationStatus, "notification_status"),
        nullable=False,
        default=NotificationStatus.pending,
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
