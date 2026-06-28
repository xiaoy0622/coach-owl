"""Outbox processor (CO-N01): deliver pending, due notifications.

Picks ``pending`` rows whose ``scheduled_for`` has arrived (or is null) and hands
each to the channel's adapter, then records a terminal status. Properties:

- **No double-send.** Rows are claimed with ``FOR UPDATE SKIP LOCKED`` so two
  concurrent processors never grab the same row, and only ``pending`` rows are
  selected — an already-``sent`` row is never reconsidered.
- **Retry-safe across a crash.** The adapter call and the ``pending -> sent``
  status transition commit together in one transaction. If the process dies
  mid-batch before commit, the rows stay ``pending`` (no committed external
  effect for the console adapter) and a later run reprocesses them. Real network
  adapters should additionally carry a provider-side idempotency key.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.enums import NotificationStatus
from app.models.notifications import Notification
from app.notifications.adapters import SendResult, default_registry
from app.notifications.adapters.registry import AdapterRegistry

_DEFAULT_BATCH = 100


@dataclass(frozen=True)
class OutboxResult:
    """Counts from one processor run."""

    processed: int
    sent: int
    failed: int


def _due(now: datetime):
    return or_(
        Notification.scheduled_for.is_(None),
        Notification.scheduled_for <= now,
    )


def process_outbox(
    db: Session,
    *,
    registry: AdapterRegistry = default_registry,
    now: datetime | None = None,
    limit: int = _DEFAULT_BATCH,
) -> OutboxResult:
    """Deliver up to ``limit`` pending, due notifications via the registry."""
    now = now or datetime.now(UTC)
    stmt = (
        select(Notification)
        .where(Notification.status == NotificationStatus.pending)
        .where(_due(now))
        .order_by(Notification.created_at.asc(), Notification.id.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    rows = db.scalars(stmt).all()

    sent = failed = 0
    for note in rows:
        try:
            adapter = registry.get(note.channel)
            result = adapter.send(note)
        except Exception as exc:  # noqa: BLE001 — one bad row can't kill the batch
            result = SendResult.failure(str(exc))

        if result.ok:
            note.status = NotificationStatus.sent
            note.sent_at = now
            note.error = None
            sent += 1
        else:
            note.status = NotificationStatus.failed
            note.error = result.error
            failed += 1

    db.commit()
    return OutboxResult(processed=len(rows), sent=sent, failed=failed)
