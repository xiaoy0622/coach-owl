"""Channel-agnostic dispatcher (CO-N01).

``notify`` is the *only* entry point business logic uses to raise a notification.
It writes one row to the ``notifications`` outbox and enforces idempotency on
``dedupe_key`` (§4 invariant 3): the same key never produces two rows — a repeat
call returns the existing row instead. Callers never name a channel beyond a
``channel`` enum value; how it is delivered is the adapters' concern.

Delivery itself is deferred: the outbox processor
(:mod:`app.notifications.processor`) picks rows up later and hands them to the
registered adapter. This write/deliver split is what makes reminders idempotent
and retry-safe.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import NotificationChannel, NotificationStatus
from app.models.notifications import Notification


def find_by_dedupe_key(db: Session, dedupe_key: str) -> Notification | None:
    return db.scalar(
        select(Notification).where(Notification.dedupe_key == dedupe_key)
    )


def notify(
    db: Session,
    *,
    org_id: uuid.UUID,
    channel: NotificationChannel = NotificationChannel.email,
    template: str,
    recipient: str,
    payload: dict | None = None,
    dedupe_key: str,
    scheduled_for: datetime | None = None,
) -> Notification:
    """Enqueue a notification on the outbox, idempotent on ``dedupe_key``.

    Returns the freshly-created row, or — if a row with this ``dedupe_key``
    already exists — that existing row (no second send is ever queued). The
    ``dedupe_key`` UNIQUE constraint backstops the read-then-insert against a
    concurrent writer racing on the same key.
    """
    existing = find_by_dedupe_key(db, dedupe_key)
    if existing is not None:
        return existing

    note = Notification(
        org_id=org_id,
        channel=channel,
        template=template,
        recipient=recipient,
        payload=payload or {},
        dedupe_key=dedupe_key,
        status=NotificationStatus.pending,
        scheduled_for=scheduled_for,
    )
    db.add(note)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent caller inserted the same dedupe_key first — yield to it.
        db.rollback()
        winner = find_by_dedupe_key(db, dedupe_key)
        if winner is None:
            raise
        return winner
    db.refresh(note)
    return note
