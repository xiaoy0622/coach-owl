"""Organization settings endpoints (CO-F03)."""
from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentOrg, RequireOwner
from app.core.errors import AppError
from app.models.organization import Organization
from app.schemas.org import OrgOut, OrgUpdate

router = APIRouter(prefix="/org", tags=["org"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=OrgOut)
def get_org(org_id: CurrentOrg, db: DbSession) -> OrgOut:
    org = db.get(Organization, org_id)
    if org is None:
        raise AppError("Org not found", code="not_found", status_code=404)
    return OrgOut.model_validate(org)


@router.patch("", response_model=OrgOut)
def update_org(
    body: OrgUpdate, principal: RequireOwner, db: DbSession
) -> OrgOut:
    org = db.get(Organization, principal.org_id)
    if org is None:
        raise AppError("Org not found", code="not_found", status_code=404)

    data = body.model_dump(exclude_unset=True)
    if "gst_rate" in data and data["gst_rate"] is not None:
        data["gst_rate"] = Decimal(str(data["gst_rate"]))
    for field, value in data.items():
        setattr(org, field, value)
    db.commit()
    db.refresh(org)
    return OrgOut.model_validate(org)
