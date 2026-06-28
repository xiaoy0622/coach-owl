"""Smart-import router (CO-S04).

Mounted at ``/students/import`` so the flow lives under the students domain:
    POST /students/import/parse          → parse raw text into review candidates
    GET  /students/import/{job_id}       → reload a job (deep-link / refresh-safe)
    POST /students/import/{job_id}/commit→ persist confirmed candidates
    POST /students/import/{job_id}/discard

The parse step never writes students; the user always confirms before commit.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentOrg
from app.schemas.imports import (
    ImportCommitRequest,
    ImportJobOut,
    ImportParseRequest,
)
from app.services import imports as service

router = APIRouter(prefix="/students/import", tags=["imports"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/parse", response_model=ImportJobOut, status_code=201)
def parse_import(body: ImportParseRequest, org_id: CurrentOrg, db: DbSession):
    job = service.create_parse_job(db, org_id, body.raw_input)
    return ImportJobOut.model_validate(job)


@router.get("/{job_id}", response_model=ImportJobOut)
def get_import(job_id: uuid.UUID, org_id: CurrentOrg, db: DbSession):
    return ImportJobOut.model_validate(service.get_job(db, org_id, job_id))


@router.post("/{job_id}/commit", response_model=ImportJobOut)
def commit_import(
    job_id: uuid.UUID,
    body: ImportCommitRequest,
    org_id: CurrentOrg,
    db: DbSession,
):
    job = service.commit_job(db, org_id, job_id, body.parsed)
    return ImportJobOut.model_validate(job)


@router.post("/{job_id}/discard", response_model=ImportJobOut)
def discard_import(job_id: uuid.UUID, org_id: CurrentOrg, db: DbSession):
    return ImportJobOut.model_validate(service.discard_job(db, org_id, job_id))
