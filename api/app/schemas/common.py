"""Shared schema primitives: camelCase base, money/decimal types, pagination."""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

# §5: amounts are stringified decimals to avoid float drift on the wire.
Money = Annotated[
    Decimal, PlainSerializer(lambda v: f"{v:.2f}", return_type=str, when_used="json")
]
Rate = Annotated[
    Decimal, PlainSerializer(lambda v: f"{v:.4f}", return_type=str, when_used="json")
]


class CamelModel(BaseModel):
    """Base model: camelCase JSON aliases, accept snake_case on input too."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


T = TypeVar("T")


class Page(CamelModel, Generic[T]):
    """Cursor-paginated list envelope (§5: ``?limit&cursor``)."""

    items: list[T]
    next_cursor: str | None = None


class ErrorDetail(CamelModel):
    code: str
    message: str
    details: object | None = None


class ErrorResponse(CamelModel):
    error: ErrorDetail
