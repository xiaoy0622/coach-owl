"""Share links router (CO-W06).

Management endpoints are org-scoped (Bearer auth): create / list / revoke a
read-only share link for one of your students. The public endpoint takes a bare
token and has **no** auth dependency — it resolves to exactly one student's
upcoming schedule + credit balance and leaks nothing else.

Note: the public route lives under this router's ``/share-links`` prefix
(``GET /api/v1/share-links/public/{token}``) so registration stays append-only —
it does not add the ``current_org`` dependency, so it is reachable without a
token. Times are ISO8601 UTC; the page renders them in the org timezone.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentOrg
from app.schemas.common import Page
from app.schemas.share_links import (
    PublicShareOut,
    ShareLinkCreate,
    ShareLinkOut,
)
from app.services import share_links as service

router = APIRouter(prefix="/share-links", tags=["share_links"])

DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=Page[ShareLinkOut])
def list_share_links(
    org_id: CurrentOrg,
    db: DbDep,
    student_id: Annotated[uuid.UUID | None, Query(alias="studentId")] = None,
):
    """List this org's share links (optionally filtered to one student)."""
    links = service.list_share_links(db, org_id, student_id)
    return Page[ShareLinkOut](
        items=[ShareLinkOut.model_validate(link) for link in links]
    )


@router.post("", response_model=ShareLinkOut, status_code=201)
def create_share_link(body: ShareLinkCreate, org_id: CurrentOrg, db: DbDep):
    """Create a read-only share link for one of this org's students."""
    link = service.create_share_link(db, org_id, body)
    return ShareLinkOut.model_validate(link)


@router.delete("/{link_id}", status_code=204)
def revoke_share_link(link_id: uuid.UUID, org_id: CurrentOrg, db: DbDep):
    """Revoke (delete) a share link. The token stops resolving immediately."""
    service.revoke_share_link(db, org_id, link_id)


@router.get("/public/{token}", response_model=PublicShareOut)
def resolve_public_share(token: str, db: DbDep):
    """PUBLIC, no-auth: resolve a token → one student's schedule + balance."""
    return service.resolve_public_share(db, token)
