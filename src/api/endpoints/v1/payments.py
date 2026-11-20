from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.connections.database import get_db
from src.data.models import User
from src.schemas.payment import (
    PaymentCallbackResponse, PaymentResponse, PaymentStartResponse, WalletTopUpCreate,
)
from src.services.payment_service import (
    PaymentConflictError, PaymentService,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/wallet/top-up",
    response_model=PaymentStartResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_wallet_top_up(
    payload: WalletTopUpCreate,
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", min_length=8, max_length=255
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        payment, redirect_url = PaymentService.create_wallet_top_up(
            db,
            user_id=current_user.id,
            amount_rial=payload.amount_rial,
            idempotency_key=idempotency_key or "",
        )
        return {"payment": payment, "redirect_url": redirect_url}
    except PaymentConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/zarinpal/callback",
    response_model=PaymentCallbackResponse,
)
def zarinpal_callback(
    payment_id: int = Query(gt=0),
    token: str = Query(min_length=20, max_length=100),
    authority: str | None = Query(default=None, alias="Authority"),
    gateway_status: str | None = Query(default=None, alias="Status"),
    db: Session = Depends(get_db),
):
    try:
        return PaymentService.handle_zarinpal_callback(
            db,
            payment_id=payment_id,
            token=token,
            authority=authority,
            status=gateway_status,
        )
    except PaymentConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_my_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return PaymentService.get_user_payment(db, payment_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
