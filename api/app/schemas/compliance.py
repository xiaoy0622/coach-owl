"""Compliance schemas (CO-X03): account hard-delete request/response.

The data-export endpoint returns a generic, already-JSON-serialized document
(decimals stringified, datetimes ISO8601) built in ``app.services.compliance``;
it does not need a typed envelope here.
"""
from __future__ import annotations

from app.schemas.common import CamelModel


class AccountDeleteRequest(CamelModel):
    """Confirmation guard: ``confirm`` must equal the org's exact name."""

    confirm: str


class AccountDeleteResponse(CamelModel):
    """Summary of the irreversible hard-delete: rows removed per entity."""

    org_id: str
    deleted: dict[str, int]
