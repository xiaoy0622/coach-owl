"""Organization contracts."""
from __future__ import annotations

import uuid

from pydantic import Field

from app.schemas.common import CamelModel, Rate


class OrgOut(CamelModel):
    id: uuid.UUID
    name: str
    timezone: str
    currency: str
    gst_enabled: bool
    gst_rate: Rate
    abn: str | None = None
    brand_name: str | None = None


class OrgUpdate(CamelModel):
    name: str | None = Field(default=None, max_length=255)
    timezone: str | None = None
    currency: str | None = Field(default=None, max_length=3)
    gst_enabled: bool | None = None
    gst_rate: float | None = Field(default=None, ge=0, le=1)
    abn: str | None = Field(default=None, max_length=20)
    brand_name: str | None = Field(default=None, max_length=255)
