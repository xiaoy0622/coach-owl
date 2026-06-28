"""Read-only share links (student/guardian schedule, no login)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, OrgScopedMixin


class ShareLink(OrgScopedMixin, Base):
    __tablename__ = "share_links"
    __table_args__ = (
        UniqueConstraint("token", name="uq_share_links_token"),
    )

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
