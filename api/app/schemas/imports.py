"""Smart-import contracts (CO-S04). AI candidates require confirm before commit."""
from __future__ import annotations

import uuid
from datetime import datetime

from app.models.enums import ImportStatus
from app.schemas.common import CamelModel


class ImportParseRequest(CamelModel):
    """Raw CSV / pasted text fed to the LLM parser."""

    raw_input: str


class ImportJobOut(CamelModel):
    id: uuid.UUID
    org_id: uuid.UUID
    raw_input: str
    parsed: dict
    status: ImportStatus
    created_at: datetime


class ImportCommitRequest(CamelModel):
    """User-confirmed/edited candidate structure to persist."""

    parsed: dict
