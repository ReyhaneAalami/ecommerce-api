from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_admin, get_current_vendor
from src.connections.database import get_db
from src.data.models import User, Vendor
from src.schemas.payout import PayoutCreate, PayoutDecision, PayoutResponse, PayoutListResponse
from src.services.payout_service import PayoutConflictError, PayoutService

router = APIRouter(prefix="/payouts", tags=["Vendor Payouts"])


@router.post("/me", response_model=PayoutResponse, status_code=status.HTTP_201_CREATED)
def create_payout(data: PayoutCreate, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", min_length=8, max_length=255), vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    if vendor.status != "approved":
        raise HTTPException(status_code=403, detail="Only approved vendors can request payouts.")
    try:
        return PayoutService.create(db, vendor_id=vendor.id, user_id=vendor.user_id, data=data, idempotency_key=idempotency_key)
    except PayoutConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/me", response_model=PayoutListResponse)
def my_payouts(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    return PayoutService.list_vendor(db, vendor.id, skip, limit)


@router.get("/admin", response_model=PayoutListResponse)
def admin_payouts(status_filter: Literal["pending", "approved", "rejected", "paid"] | None = Query(default=None, alias="status"), skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return PayoutService.list_admin(db, status_filter, skip, limit)


@router.patch("/admin/{request_id}/decision", response_model=PayoutResponse)
def decide_payout(request_id: int, data: PayoutDecision, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    try:
        return PayoutService.decide(db, request_id, admin.id, data.decision, data.admin_note, data.transfer_reference)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
