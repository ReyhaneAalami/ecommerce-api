from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.connections.database import get_db
from src.api.dependencies import get_current_user
from src.data.models import User
from src.schemas.wallet import (
    WalletResponse,
    WalletTransactionListResponse,
)
from src.services.wallet_service import WalletService


router = APIRouter(
    prefix="/wallets",
    tags=["Wallets"],
)


@router.get(
    "/me",
    response_model=WalletResponse,
)
def get_my_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return WalletService.get_wallet(
            db,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/me/transactions",
    response_model=WalletTransactionListResponse,
)
def get_my_wallet_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return WalletService.get_transactions(
            db,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc