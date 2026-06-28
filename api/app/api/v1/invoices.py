"""Invoices router — generation + PDF; service is Wave 3 (CO-P02)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.deps import CurrentOrg
from app.core.errors import not_implemented
from app.schemas.common import Page
from app.schemas.invoices import InvoiceCreate, InvoiceOut

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=Page[InvoiceOut])
def list_invoices(org_id: CurrentOrg):
    not_implemented()


@router.post("", response_model=InvoiceOut, status_code=201)
def create_invoice(body: InvoiceCreate, org_id: CurrentOrg):
    not_implemented()


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: uuid.UUID, org_id: CurrentOrg):
    not_implemented()
