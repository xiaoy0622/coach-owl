"""ORM model registry. Importing this module registers every table on Base."""
from __future__ import annotations

from app.core.db import Base
from app.models.billing import Invoice, Payment
from app.models.credits import CreditLedger, CreditPack
from app.models.import_jobs import ImportJob
from app.models.lesson_notes import LessonNote
from app.models.notifications import Notification
from app.models.organization import Organization
from app.models.scheduling import Lesson, RecurrenceRule
from app.models.share_links import ShareLink
from app.models.student import Guardian, Student
from app.models.user import User

__all__ = [
    "Base",
    "Organization",
    "User",
    "Student",
    "Guardian",
    "RecurrenceRule",
    "Lesson",
    "CreditPack",
    "CreditLedger",
    "Payment",
    "Invoice",
    "Notification",
    "LessonNote",
    "ShareLink",
    "ImportJob",
]
