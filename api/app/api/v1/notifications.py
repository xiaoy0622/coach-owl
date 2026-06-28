"""Notifications router (CO-N01): org-scoped outbox + dev triggers.

``GET /notifications`` lists the outbox (filterable by status). The ``POST``
trigger and ``POST /notifications/process`` flush are convenience endpoints for
dev/testing the channel-agnostic pipeline; in production reminders are raised by
domain services (via the dispatcher) and delivered by the ARQ worker. JSON is
camelCase.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentOrg
from app.models.enums import NotificationStatus
from app.schemas.common import Page
from app.schemas.notifications import (
    NotificationCreate,
    NotificationOut,
    OutboxRunOut,
)
from app.services import notifications as service

router = APIRouter(prefix="/notifications", tags=["notifications"])

DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=Page[NotificationOut])
def list_notifications(
    org_id: CurrentOrg,
    db: DbDep,
    status: NotificationStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
):
    """List this org's outbox rows, newest-cursor last, filterable by status."""
    items, next_cursor = service.list_notifications(
        db, org_id, status=status, limit=limit, cursor=cursor
    )
    return Page[NotificationOut](
        items=[NotificationOut.model_validate(n) for n in items],
        next_cursor=next_cursor,
    )


@router.post("", response_model=NotificationOut, status_code=201)
def enqueue_notification(
    body: NotificationCreate, org_id: CurrentOrg, db: DbDep
):
    """Dev/test trigger: enqueue a notification (idempotent on ``dedupeKey``)."""
    note = service.enqueue(db, org_id, body)
    return NotificationOut.model_validate(note)


@router.post("/process", response_model=OutboxRunOut)
def process_outbox(org_id: CurrentOrg, db: DbDep):
    """Dev/test trigger: flush pending, due notifications via their adapters."""
    result = service.run_outbox(db)
    return OutboxRunOut(
        processed=result.processed, sent=result.sent, failed=result.failed
    )
