"""Compliance service (CO-X03): org-scoped data export + hard account delete.

Privacy Act / APPs: an org owner can (1) export every row their tenant holds and
(2) permanently erase the tenant and all its data. Both operations are strictly
``org_id``-scoped — they can never read or delete another tenant's rows.

Serialization convention (§5): decimals are emitted as strings, datetimes/dates
as ISO8601, UUIDs as strings, so the export document is wire-safe JSON.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import delete, inspect, select
from sqlalchemy.orm import Session

from app.core.deps import scoped
from app.models import (
    CreditLedger,
    CreditPack,
    Guardian,
    ImportJob,
    Invoice,
    Lesson,
    LessonNote,
    Notification,
    Organization,
    Payment,
    RecurrenceRule,
    ShareLink,
    Student,
    User,
)

# Export layout: top-level key -> ORM model. ``organization`` is handled
# separately (single object, keyed by its own id rather than ``org_id``).
EXPORT_MODELS: dict[str, type] = {
    "users": User,
    "students": Student,
    "guardians": Guardian,
    "recurrence_rules": RecurrenceRule,
    "lessons": Lesson,
    "credit_packs": CreditPack,
    "credit_ledger": CreditLedger,
    "payments": Payment,
    "invoices": Invoice,
    "notifications": Notification,
    "lesson_notes": LessonNote,
    "share_links": ShareLink,
    "import_jobs": ImportJob,
}

# FK-safe deletion order: dependents first, parents last. Notably ``lessons``
# must precede ``users`` because ``lessons.coach_id`` -> ``users.id`` is
# ON DELETE RESTRICT; every other intra-org FK is CASCADE or SET NULL, but we
# delete explicitly (rather than relying on the org cascade) so the RESTRICT
# edge can never fire mid-cascade. ``organizations`` is removed last.
DELETE_ORDER: list[type] = [
    LessonNote,
    CreditLedger,
    Payment,
    Invoice,
    ShareLink,
    Lesson,
    RecurrenceRule,
    CreditPack,
    Guardian,
    Notification,
    ImportJob,
    Student,
    User,
]


def _jsonify(value: Any) -> Any:
    """Coerce an ORM column value into a JSON-safe primitive (see §5)."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list | tuple):
        return [_jsonify(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    return value


def _row_to_dict(obj: Any) -> dict[str, Any]:
    """Serialize every mapped column of an ORM row to JSON-safe primitives."""
    mapper = inspect(obj).mapper
    return {attr.key: _jsonify(getattr(obj, attr.key)) for attr in mapper.column_attrs}


def export_org_data(db: Session, org_id: uuid.UUID) -> dict[str, Any]:
    """Return a single JSON-safe document of EVERY row owned by ``org_id``.

    Each collection query is funnelled through ``scoped(...)`` so no other
    tenant's rows can appear in the dump.
    """
    org = db.get(Organization, org_id)
    document: dict[str, Any] = {
        "organization": _row_to_dict(org) if org is not None else None,
    }
    for key, model in EXPORT_MODELS.items():
        rows = db.scalars(scoped(select(model), org_id, model)).all()
        document[key] = [_row_to_dict(r) for r in rows]
    return document


def hard_delete_org(db: Session, org_id: uuid.UUID) -> dict[str, int]:
    """Permanently delete the org and ALL its data in FK-safe order.

    Runs inside the caller's transaction (a single ``commit`` at the end). Every
    bulk delete is ``org_id``-scoped, so a caller can only erase their own
    tenant. Returns a per-entity count of deleted rows.
    """
    deleted: dict[str, int] = {}
    for model in DELETE_ORDER:
        result = db.execute(
            delete(model).where(model.org_id == org_id)
        )
        deleted[model.__tablename__] = result.rowcount or 0

    org_result = db.execute(
        delete(Organization).where(Organization.id == org_id)
    )
    deleted[Organization.__tablename__] = org_result.rowcount or 0

    db.commit()
    return deleted
