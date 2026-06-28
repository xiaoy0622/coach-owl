"""Invoices router — generation, retrieval + PDF download (CO-P02)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentOrg
from app.schemas.common import Page
from app.schemas.invoices import InvoiceCreate, InvoiceOut
from app.services import invoices as invoices_service

router = APIRouter(prefix="/invoices", tags=["invoices"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=Page[InvoiceOut])
def list_invoices(org_id: CurrentOrg, db: DbSession):
    rows = invoices_service.list_invoices(db, org_id)
    return Page(items=[InvoiceOut.model_validate(i) for i in rows])


@router.post("", response_model=InvoiceOut, status_code=201)
def create_invoice(body: InvoiceCreate, org_id: CurrentOrg, db: DbSession):
    invoice = invoices_service.create_invoice(db, org_id, body)
    return InvoiceOut.model_validate(invoice)


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: uuid.UUID, org_id: CurrentOrg, db: DbSession):
    invoice = invoices_service.get_invoice(db, org_id, invoice_id)
    return InvoiceOut.model_validate(invoice)


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: uuid.UUID, org_id: CurrentOrg, db: DbSession
):
    invoice = invoices_service.get_invoice(db, org_id, invoice_id)
    pdf_bytes = invoices_service.render_pdf(db, org_id, invoice)
    filename = f"invoice-{invoice.number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )
