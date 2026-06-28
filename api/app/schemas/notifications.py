"""Notification contracts (CO-N01)."""
from __future__ import annotations

import uuid
from datetime import datetime

from app.models.enums import NotificationChannel, NotificationStatus
from app.schemas.common import CamelModel


class NotificationCreate(CamelModel):
    channel: NotificationChannel = NotificationChannel.email
    template: str
    recipient: str
    payload: dict = {}
    dedupe_key: str
    scheduled_for: datetime | None = None


class NotificationOut(CamelModel):
    id: uuid.UUID
    org_id: uuid.UUID
    channel: NotificationChannel
    template: str
    recipient: str
    payload: dict
    dedupe_key: str
    status: NotificationStatus
    scheduled_for: datetime | None = None
    sent_at: datetime | None = None
    error: str | None = None
    created_at: datetime
