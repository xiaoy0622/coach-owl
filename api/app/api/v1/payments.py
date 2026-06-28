"""Payments router — records + revenue overview; service is Wave 2 (CO-P01)."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentOrg
from app.core.errors import not_implemented
from app.schemas.common import Page
from app.schemas.payments import PaymentCreate, PaymentOut, RevenueOverview

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=Page[PaymentOut])
def list_payments(org_id: CurrentOrg):
    not_implemented()


@router.post("", response_model=PaymentOut, status_code=201)
def record_payment(body: PaymentCreate, org_id: CurrentOrg):
    not_implemented()


@router.get("/overview", response_model=RevenueOverview)
def revenue_overview(org_id: CurrentOrg):
    not_implemented()
