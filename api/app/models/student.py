"""Students and their guardians (CRM-lite)."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, OrgScopedMixin
from app.models._types import str_enum
from app.models.enums import StudentStatus


class Student(OrgScopedMixin, Base):
    __tablename__ = "students"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[StudentStatus] = mapped_column(
        str_enum(StudentStatus, "student_status"),
        nullable=False,
        default=StudentStatus.active,
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Guardian(OrgScopedMixin, Base):
    """Guardian for a (typically minor) student; privacy-flagged per APPs."""

    __tablename__ = "guardians"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
