"""Credits router — packs / ledger / balance / deduct (CO-K01)."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentOrg
from app.schemas.common import Page
from app.schemas.credits import (
    BalanceOut,
    CreditDeductRequest,
    CreditPackCreate,
    CreditPackOut,
    LedgerAdjustRequest,
    LedgerEntryOut,
)
from app.services import credits as credits_service

router = APIRouter(prefix="/credits", tags=["credits"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/packs", response_model=CreditPackOut, status_code=201)
def buy_pack(body: CreditPackCreate, org_id: CurrentOrg, db: DbSession):
    pack = credits_service.buy_pack(db, org_id, body)
    return CreditPackOut.model_validate(pack)


@router.get("/packs", response_model=Page[CreditPackOut])
def list_packs(
    org_id: CurrentOrg, db: DbSession, student_id: uuid.UUID | None = None
):
    packs = credits_service.list_packs(db, org_id, student_id)
    return Page(items=[CreditPackOut.model_validate(p) for p in packs])


@router.get("/ledger", response_model=Page[LedgerEntryOut])
def list_ledger(
    org_id: CurrentOrg, db: DbSession, student_id: uuid.UUID | None = None
):
    entries = credits_service.list_ledger(db, org_id, student_id)
    return Page(items=[LedgerEntryOut.model_validate(e) for e in entries])


@router.post("/ledger", response_model=LedgerEntryOut, status_code=201)
def adjust_ledger(body: LedgerAdjustRequest, org_id: CurrentOrg, db: DbSession):
    entry = credits_service.adjust_ledger(db, org_id, body)
    return LedgerEntryOut.model_validate(entry)


@router.post("/deduct", response_model=LedgerEntryOut, status_code=201)
def deduct_credit(body: CreditDeductRequest, org_id: CurrentOrg, db: DbSession):
    entry = credits_service.deduct(db, org_id, body)
    return LedgerEntryOut.model_validate(entry)


@router.get("/balance/{student_id}", response_model=BalanceOut)
def get_balance(
    student_id: uuid.UUID,
    org_id: CurrentOrg,
    db: DbSession,
    threshold: int = credits_service.DEFAULT_LOW_BALANCE_THRESHOLD,
):
    balance = credits_service.get_balance(db, org_id, student_id)
    return BalanceOut(
        student_id=student_id,
        balance=balance,
        threshold=threshold,
        low_balance=balance <= threshold,
    )
