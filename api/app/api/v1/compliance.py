"""Compliance router (CO-X03): data export + account hard-delete (Privacy/APPs).

- ``GET  /compliance/export``  — any authenticated user dumps their org's data.
- ``DELETE /compliance/account`` — owner-only, irreversible erase of the whole
  tenant, guarded by a name-confirmation field.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentOrg, RequireOwner
from app.core.errors import AppError
from app.models.organization import Organization
from app.schemas.compliance import AccountDeleteRequest, AccountDeleteResponse
from app.services import compliance as service

router = APIRouter(prefix="/compliance", tags=["compliance"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/export")
def export_data(org_id: CurrentOrg, db: DbSession) -> dict[str, Any]:
    """Return the full org-scoped data export as a single JSON document."""
    return service.export_org_data(db, org_id)


@router.delete("/account", response_model=AccountDeleteResponse)
def delete_account(
    body: AccountDeleteRequest, principal: RequireOwner, db: DbSession
) -> AccountDeleteResponse:
    """Permanently delete the current org and all its data (owner only).

    Requires ``confirm`` to exactly match the org's name as a guard against
    accidental destruction.
    """
    org = db.get(Organization, principal.org_id)
    if org is None:
        raise AppError("Org not found", code="not_found", status_code=404)
    if body.confirm != org.name:
        raise AppError(
            "Confirmation does not match the organization name",
            code="confirmation_mismatch",
            status_code=400,
        )

    deleted = service.hard_delete_org(db, principal.org_id)
    return AccountDeleteResponse(org_id=str(principal.org_id), deleted=deleted)
