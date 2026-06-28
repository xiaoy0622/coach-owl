"""Shared column type helpers."""
from __future__ import annotations

from enum import Enum

from sqlalchemy import Enum as SAEnum


def str_enum(enum_cls: type[Enum], name: str) -> SAEnum:
    """A VARCHAR-backed enum column with a CHECK constraint on the values.

    ``native_enum=False`` keeps migrations portable (no Postgres ENUM type to
    create/drop); ``values_callable`` stores the enum *value* string.
    """
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        validate_strings=True,
        values_callable=lambda e: [m.value for m in e],
    )
