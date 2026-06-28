"""Smart-import router — parse/commit; service is Wave 3 (CO-S04)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.deps import CurrentOrg
from app.core.errors import not_implemented
from app.schemas.imports import (
    ImportCommitRequest,
    ImportJobOut,
    ImportParseRequest,
)

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/parse", response_model=ImportJobOut, status_code=201)
def parse_import(body: ImportParseRequest, org_id: CurrentOrg):
    # LLM parse -> import_jobs(status=review); confirm before commit.
    not_implemented()


@router.post("/{job_id}/commit", response_model=ImportJobOut)
def commit_import(job_id: uuid.UUID, body: ImportCommitRequest, org_id: CurrentOrg):
    not_implemented()
