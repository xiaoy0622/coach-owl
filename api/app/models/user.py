"""User (owner/coach), scoped to an organization."""
from __future__ import annotations

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, OrgScopedMixin
from app.models._types import str_enum
from app.models.enums import UserRole


class User(OrgScopedMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        str_enum(UserRole, "user_role"),
        nullable=False,
        default=UserRole.owner,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
