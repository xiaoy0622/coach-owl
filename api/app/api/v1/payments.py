"""Payments router — records + revenue overview (CO-P01)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentOrg
from app.schemas.common import Page
from app.schemas.payments import PaymentCreate, PaymentOut, RevenueOverview
from app.services import payments as payments_service

router = APIRouter(prefix="/payments", tags=["payments"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=Page[PaymentOut])
def list_payments(org_id: CurrentOrg, db: DbSession):
    rows = payments_service.list_payments(db, org_id)
    return Page(items=[PaymentOut.model_validate(p) for p in rows])


@router.post("", response_model=PaymentOut, status_code=201)
def record_payment(body: PaymentCreate, org_id: CurrentOrg, db: DbSession):
    payment = payments_service.record_payment(db, org_id, body)
    return PaymentOut.model_validate(payment)


@router.get("/overview", response_model=RevenueOverview)
def revenue_overview(org_id: CurrentOrg, db: DbSession):
    return payments_service.revenue_overview(db, org_id)
