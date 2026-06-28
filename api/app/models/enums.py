"""Shared string enums for the data model (used by both ORM and schemas)."""
from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    owner = "owner"
    coach = "coach"


class StudentStatus(str, Enum):
    active = "active"
    paused = "paused"
    churned = "churned"


class RecurrenceFreq(str, Enum):
    weekly = "weekly"


class LessonStatus(str, Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"


class LedgerReason(str, Enum):
    purchase = "purchase"
    deduct = "deduct"
    refund = "refund"
    adjust = "adjust"


class PaymentMethod(str, Enum):
    cash = "cash"
    transfer = "transfer"
    other = "other"


class PaymentStatus(str, Enum):
    paid = "paid"
    due = "due"


class InvoiceStatus(str, Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"


class NotificationChannel(str, Enum):
    email = "email"


class NotificationStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class NoteSource(str, Enum):
    text = "text"
    voice = "voice"


class ImportStatus(str, Enum):
    parsing = "parsing"
    review = "review"
    committed = "committed"
    discarded = "discarded"


def sa_enum_values(enum_cls: type[Enum]) -> list[str]:
    return [e.value for e in enum_cls]
