"""Share links router — read-only schedule; service is Wave 4 (CO-W06)."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentOrg
from app.core.errors import not_implemented
from app.schemas.common import Page
from app.schemas.share_links import ShareLinkCreate, ShareLinkOut

router = APIRouter(prefix="/share-links", tags=["share_links"])


@router.get("", response_model=Page[ShareLinkOut])
def list_share_links(org_id: CurrentOrg):
    not_implemented()


@router.post("", response_model=ShareLinkOut, status_code=201)
def create_share_link(body: ShareLinkCreate, org_id: CurrentOrg):
    not_implemented()
