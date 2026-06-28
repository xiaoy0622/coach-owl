"""Invoice service: GST-aware totals, org-sequential numbers, PDF (CO-P02).

Totals honour the org's ``gst_enabled`` flag via the localization util
(subtotal -> GST 10% -> total). Invoice numbers are sequential *per org*; a
Postgres advisory lock serializes concurrent allocations so two invoices in the
same org can't collide on ``number`` (there's also a unique constraint as a
backstop). The PDF is rendered with fpdf2 (pure-python) and includes the org's
brand name + ABN, AUD amounts and DD/MM/YYYY dates.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.billing import Invoice
from app.models.organization import Organization
from app.models.student import Student
from app.schemas.invoices import InvoiceCreate
from app.utils.localization import (
    calc_gst,
    format_aud,
    format_date_au,
    now_utc,
    round_money,
)


def _require_student(db: Session, org_id: uuid.UUID, student_id: uuid.UUID) -> Student:
    student = db.scalar(
        select(Student).where(
            Student.id == student_id, Student.org_id == org_id
        )
    )
    if student is None:
        raise AppError("Student not found", code="not_found", status_code=404)
    return student


def _next_number(db: Session, org_id: uuid.UUID) -> int:
    """Allocate the next per-org invoice number under an advisory lock."""
    # Stable signed 64-bit key from the org uuid for the advisory lock.
    key = int.from_bytes(org_id.bytes[:8], "big", signed=True)
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": key})
    current = db.scalar(
        select(Invoice.number)
        .where(Invoice.org_id == org_id)
        .order_by(Invoice.number.desc())
        .limit(1)
    )
    return (current or 0) + 1


def _line_items_json(body: InvoiceCreate) -> tuple[list[dict], Decimal]:
    """Serialize line items for JSONB (decimals as strings) + subtotal."""
    items: list[dict] = []
    subtotal = Decimal("0.00")
    for li in body.line_items:
        amount = round_money(li.amount)
        subtotal += amount
        items.append(
            {
                "description": li.description,
                "quantity": li.quantity,
                "unit_price": str(round_money(li.unit_price)),
                "amount": str(amount),
            }
        )
    return items, round_money(subtotal)


def create_invoice(
    db: Session, org_id: uuid.UUID, body: InvoiceCreate
) -> Invoice:
    if not body.line_items:
        raise AppError(
            "At least one line item is required",
            code="empty_invoice",
            status_code=400,
        )
    _require_student(db, org_id, body.student_id)
    org = db.get(Organization, org_id)

    items, subtotal = _line_items_json(body)
    breakdown = calc_gst(
        subtotal,
        gst_enabled=bool(org and org.gst_enabled),
        gst_rate=(org.gst_rate if org is not None else Decimal("0.10")),
    )

    number = _next_number(db, org_id)
    invoice = Invoice(
        org_id=org_id,
        student_id=body.student_id,
        number=number,
        line_items=items,
        subtotal=breakdown.subtotal,
        gst_amount=breakdown.gst_amount,
        total=breakdown.total,
        status=body.status,
        issued_at=now_utc(),
    )
    db.add(invoice)
    db.flush()  # assign invoice.id
    # The downloadable PDF is served on demand from this canonical path.
    invoice.pdf_url = f"/api/v1/invoices/{invoice.id}/pdf"
    db.commit()
    db.refresh(invoice)
    return invoice


def list_invoices(db: Session, org_id: uuid.UUID) -> Sequence[Invoice]:
    stmt = (
        select(Invoice)
        .where(Invoice.org_id == org_id)
        .order_by(Invoice.number.desc())
    )
    return list(db.scalars(stmt))


def get_invoice(
    db: Session, org_id: uuid.UUID, invoice_id: uuid.UUID
) -> Invoice:
    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == invoice_id, Invoice.org_id == org_id
        )
    )
    if invoice is None:
        raise AppError("Invoice not found", code="not_found", status_code=404)
    return invoice


def render_pdf(db: Session, org_id: uuid.UUID, invoice: Invoice) -> bytes:
    """Render an invoice to PDF bytes (brand/ABN, AUD, DD/MM/YYYY)."""
    org = db.get(Organization, org_id)
    student = db.get(Student, invoice.student_id)
    brand = (org.brand_name or org.name) if org is not None else "CoachOwl"
    abn = org.abn if org is not None else None
    gst_enabled = bool(org and org.gst_enabled)

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    nl = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}

    # Header — brand + TAX INVOICE / INVOICE.
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, brand, **nl)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, "TAX INVOICE" if gst_enabled else "INVOICE", **nl)
    pdf.set_text_color(0, 0, 0)
    if abn:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"ABN: {abn}", **nl)
    pdf.ln(3)

    # Meta — number, date, bill-to.
    issued = invoice.issued_at or now_utc()
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, f"Invoice #: {invoice.number}", **nl)
    pdf.cell(0, 6, f"Date: {format_date_au(issued)}", **nl)
    pdf.cell(0, 6, f"Status: {invoice.status.value.title()}", **nl)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Bill to:", **nl)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 6, student.name if student is not None else "-", **nl)
    pdf.ln(4)

    # Line items table.
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(90, 8, "Description", border=1, fill=True)
    pdf.cell(20, 8, "Qty", border=1, align="R", fill=True)
    pdf.cell(35, 8, "Unit", border=1, align="R", fill=True)
    pdf.cell(35, 8, "Amount", border=1, align="R", fill=True, **nl)

    pdf.set_font("Helvetica", "", 10)
    for li in invoice.line_items:
        pdf.cell(90, 8, str(li.get("description", ""))[:48], border=1)
        pdf.cell(20, 8, str(li.get("quantity", "")), border=1, align="R")
        pdf.cell(
            35, 8, format_aud(li.get("unit_price", 0)), border=1, align="R"
        )
        pdf.cell(
            35, 8, format_aud(li.get("amount", 0)), border=1, align="R", **nl
        )

    # Totals.
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)

    def _total_row(label: str, value: Decimal, bold: bool = False) -> None:
        pdf.set_font("Helvetica", "B" if bold else "", 11)
        pdf.cell(145, 7, label, align="R")
        pdf.cell(35, 7, format_aud(value), align="R", **nl)

    _total_row("Subtotal", invoice.subtotal)
    if gst_enabled:
        _total_row("GST (10%)", invoice.gst_amount)
    _total_row("Total (AUD)", invoice.total, bold=True)

    out = pdf.output()
    return bytes(out)
