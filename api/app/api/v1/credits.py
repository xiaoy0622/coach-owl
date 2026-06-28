"""Credits router — packs/ledger/balance; service is Wave 2 (CO-K01)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.core.deps import CurrentOrg
from app.core.errors import not_implemented
from app.schemas.common import Page
from app.schemas.credits import (
    BalanceOut,
    CreditPackCreate,
    CreditPackOut,
    LedgerAdjustRequest,
    LedgerEntryOut,
)

router = APIRouter(prefix="/credits", tags=["credits"])


@router.post("/packs", response_model=CreditPackOut, status_code=201)
def buy_pack(body: CreditPackCreate, org_id: CurrentOrg):
    not_implemented()


@router.get("/packs", response_model=Page[CreditPackOut])
def list_packs(org_id: CurrentOrg, student_id: uuid.UUID | None = None):
    not_implemented()


@router.get("/ledger", response_model=Page[LedgerEntryOut])
def list_ledger(org_id: CurrentOrg, student_id: uuid.UUID | None = None):
    not_implemented()


@router.post("/ledger", response_model=LedgerEntryOut, status_code=201)
def adjust_ledger(body: LedgerAdjustRequest, org_id: CurrentOrg):
    not_implemented()


@router.get("/balance/{student_id}", response_model=BalanceOut)
def get_balance(student_id: uuid.UUID, org_id: CurrentOrg):
    not_implemented()
