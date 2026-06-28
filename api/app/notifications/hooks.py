"""Cross-domain notification helpers (thin wrappers over :func:`notify`).

These let other domains raise a notification without learning the dispatcher's
argument shape or inventing dedupe-key conventions. They deliberately take plain
values (ids, numbers, emails) so there is **no cross-domain import** — e.g. the
Credits stream (CO-K03) calls :func:`low_balance_reminder` with a balance it
already computed; it does not import a Credits model here, and this module does
not import Credits.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.enums import NotificationChannel
from app.models.notifications import Notification
from app.notifications.dispatcher import notify


def low_balance_reminder(
    db: Session,
    *,
    org_id: uuid.UUID,
    student_id: uuid.UUID,
    recipient: str,
    balance: int,
    threshold: int,
    student_name: str | None = None,
) -> Notification:
    """Raise a low-balance reminder, idempotent per (student, threshold).

    The dedupe_key embeds the threshold so crossing a *lower* threshold later
    (e.g. 5 -> 2 sessions) still notifies, while a re-scan at the same threshold
    never double-sends.
    """
    return notify(
        db,
        org_id=org_id,
        channel=NotificationChannel.email,
        template="low_balance",
        recipient=recipient,
        payload={
            "studentId": str(student_id),
            "studentName": student_name,
            "balance": balance,
            "threshold": threshold,
        },
        dedupe_key=f"student:{student_id}:low_balance:{threshold}",
    )
