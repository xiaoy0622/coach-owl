"""Notifications router — outbox; service is Wave 3 (CO-N01)."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentOrg
from app.core.errors import not_implemented
from app.schemas.common import Page
from app.schemas.notifications import NotificationCreate, NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=Page[NotificationOut])
def list_notifications(org_id: CurrentOrg):
    not_implemented()


@router.post("", response_model=NotificationOut, status_code=201)
def enqueue_notification(body: NotificationCreate, org_id: CurrentOrg):
    not_implemented()
