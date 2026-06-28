"""Invoice contracts incl. optional GST (CO-P02)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import InvoiceStatus
from app.schemas.common import CamelModel, Money


class InvoiceLineItem(CamelModel):
    description: str
    quantity: int = Field(default=1, ge=1)
    unit_price: Money
    amount: Money


class InvoiceCreate(CamelModel):
    student_id: uuid.UUID
    line_items: list[InvoiceLineItem]
    status: InvoiceStatus = InvoiceStatus.draft


class InvoiceOut(CamelModel):
    id: uuid.UUID
    org_id: uuid.UUID
    student_id: uuid.UUID
    number: int
    line_items: list[InvoiceLineItem]
    subtotal: Money
    gst_amount: Money
    total: Money
    status: InvoiceStatus
    pdf_url: str | None = None
    issued_at: datetime | None = None
    created_at: datetime
