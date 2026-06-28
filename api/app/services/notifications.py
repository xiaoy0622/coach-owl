"""Notifications app service (CO-N01): outbox listing + enqueue + flush.

Thin layer the router calls: org-scoped, cursor-paginated reads over the outbox,
plus pass-throughs to the channel-agnostic dispatcher/processor. All real send
logic lives under :mod:`app.notifications`.
"""
from __future__ import annotations

import base64
import binascii
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import scoped
from app.core.errors import AppError
from app.models.enums import NotificationStatus
from app.models.notifications import Notification
from app.notifications.dispatcher import notify
from app.notifications.processor import OutboxResult, process_outbox
from app.schemas.notifications import NotificationCreate

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def _encode_cursor(item: Notification) -> str:
    raw = f"{item.created_at.isoformat()}|{item.id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        created_raw, id_raw = raw.split("|", 1)
        return datetime.fromisoformat(created_raw), uuid.UUID(id_raw)
    except (ValueError, binascii.Error) as exc:
        raise AppError(
            "Invalid pagination cursor",
            code="invalid_cursor",
            status_code=400,
        ) from exc


def list_notifications(
    db: Session,
    org_id: uuid.UUID,
    *,
    status: NotificationStatus | None = None,
    limit: int = _DEFAULT_LIMIT,
    cursor: str | None = None,
) -> tuple[list[Notification], str | None]:
    """Org-scoped outbox list, optionally filtered by status; keyset paginated."""
    limit = max(1, min(limit, _MAX_LIMIT))
    stmt = scoped(select(Notification), org_id, Notification)
    if status is not None:
        stmt = stmt.where(Notification.status == status)
    stmt = stmt.order_by(
        Notification.created_at.asc(), Notification.id.asc()
    )
    if cursor:
        c_created, c_id = _decode_cursor(cursor)
        stmt = stmt.where(
            (Notification.created_at, Notification.id) > (c_created, c_id)
        )
    rows = db.scalars(stmt.limit(limit + 1)).all()
    has_more = len(rows) > limit
    items = list(rows[:limit])
    next_cursor = _encode_cursor(items[-1]) if has_more and items else None
    return items, next_cursor


def enqueue(
    db: Session, org_id: uuid.UUID, data: NotificationCreate
) -> Notification:
    """Enqueue via the dispatcher (idempotent on ``dedupe_key``)."""
    return notify(
        db,
        org_id=org_id,
        channel=data.channel,
        template=data.template,
        recipient=data.recipient,
        payload=data.payload,
        dedupe_key=data.dedupe_key,
        scheduled_for=data.scheduled_for,
    )


def run_outbox(db: Session, *, now: datetime | None = None) -> OutboxResult:
    """Deliver pending, due notifications (dev/test trigger for the worker job)."""
    return process_outbox(db, now=now)
