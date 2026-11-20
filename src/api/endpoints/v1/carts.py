from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.connections.database import get_db
from src.api.dependencies import get_current_customer
from src.data.models import User
from src.schemas.cart import CartItemCreate, CartItemUpdate, CartResponse
from src.schemas.order import OrderResponse
from src.services.cart_service import CartService
from src.services.order_service import IdempotencyConflictError, OrderService


router = APIRouter(prefix="/carts", tags=["Carts"])


@router.get("/me", response_model=CartResponse)
def get_my_cart(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        return CartService.get_cart(db, customer_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
def add_cart_item(
    item_data: CartItemCreate,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        return CartService.add_item(
            db,
            customer_id=current_user.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Cart item conflicts with existing data."
        ) from exc


@router.patch("/items/{product_id}", response_model=CartResponse)
def update_cart_item(
    product_id: int,
    item_data: CartItemUpdate,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        return CartService.update_item(
            db,
            customer_id=current_user.id,
            product_id=product_id,
            quantity=item_data.quantity,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/items/{product_id}", response_model=CartResponse)
def remove_cart_item(
    product_id: int,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        return CartService.remove_item(
            db, customer_id=current_user.id, product_id=product_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/clear", response_model=CartResponse)
def clear_my_cart(
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        return CartService.clear_cart(db, customer_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/checkout", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def checkout_cart(
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=8,
        max_length=255,
    ),
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        return OrderService.checkout(
            db,
            customer_id=current_user.id,
            idempotency_key=idempotency_key,
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Checkout conflicts with existing data.",
        ) from exc
