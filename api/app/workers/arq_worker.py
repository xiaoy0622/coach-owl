"""ARQ worker wiring (CO-N04): schedule the reminder scan + outbox delivery.

The schedulable jobs here are thin async shims; all real logic lives in the plain,
synchronous, unit-tested functions :func:`enqueue_reminders` and
:func:`process_outbox`. Each shim opens its own DB session and runs the sync work
in a thread so the (sync) SQLAlchemy session never blocks the event loop.

Run with::

    arq app.workers.arq_worker.WorkerSettings

Redis comes from ``settings.redis_url`` (the compose Redis on :6380).
"""
from __future__ import annotations

import asyncio
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.db import SessionLocal
from app.notifications.processor import OutboxResult, process_outbox
from app.workers.reminders import enqueue_reminders


def _scan_and_send() -> OutboxResult:
    db = SessionLocal()
    try:
        enqueue_reminders(db)
        return process_outbox(db)
    finally:
        db.close()


def _send_outbox() -> OutboxResult:
    db = SessionLocal()
    try:
        return process_outbox(db)
    finally:
        db.close()


async def scan_reminders(ctx: dict[str, Any]) -> dict[str, int]:
    """Enqueue due lesson reminders, then flush the outbox."""
    result = await asyncio.to_thread(_scan_and_send)
    return {"processed": result.processed, "sent": result.sent, "failed": result.failed}


async def deliver_outbox(ctx: dict[str, Any]) -> dict[str, int]:
    """Deliver any pending, due notifications."""
    result = await asyncio.to_thread(_send_outbox)
    return {"processed": result.processed, "sent": result.sent, "failed": result.failed}


class WorkerSettings:
    """ARQ entrypoint config."""

    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [scan_reminders, deliver_outbox]
    cron_jobs = [
        # Scan for newly-due reminders every 5 minutes.
        cron(scan_reminders, minute=set(range(0, 60, 5)), run_at_startup=True),
        # Flush the outbox twice a minute so sends aren't left waiting.
        cron(deliver_outbox, second={0, 30}),
    ]
