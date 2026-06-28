"""SQLAlchemy 2.0 engine, session factory, declarative base + shared mixins.

Tenancy: every tenant-scoped table mixes in ``OrgScopedMixin`` which adds an
indexed ``org_id`` FK. Application-level scoping is enforced via the helpers in
``app.core.deps`` (``scoped`` / ``current_org``). A Postgres RLS policy is
provided (commented) in the initial migration as defence-in-depth.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Uuid, create_engine, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
    sessionmaker,
)

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class TimestampMixin:
    """``id`` (uuid pk) + ``created_at`` / ``updated_at`` (tz-aware)."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class OrgScopedMixin(TimestampMixin):
    """Adds an indexed ``org_id`` FK for tenant-scoped tables."""

    @declared_attr
    def org_id(cls) -> Mapped[uuid.UUID]:  # noqa: N805
        return mapped_column(
            Uuid,
            ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


def get_db():
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
