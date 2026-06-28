"""Smart-import jobs: the confirm/edit intermediate state before commit."""
from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, OrgScopedMixin
from app.models._types import str_enum
from app.models.enums import ImportStatus


class ImportJob(OrgScopedMixin, Base):
    __tablename__ = "import_jobs"

    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    # LLM-extracted candidate structure (students/recurrence drafts).
    parsed: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[ImportStatus] = mapped_column(
        str_enum(ImportStatus, "import_status"),
        nullable=False,
        default=ImportStatus.parsing,
    )
