from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.connections.database import get_db
from src.api.dependencies import get_current_customer, get_current_vendor
from src.data.models import User, Vendor
from src.schemas.order import (
    OrderCreate,
    OrderResponse,
    VendorOrderResponse,
    VendorOrderStatusUpdate,
)
from src.services.order_service import (
    IdempotencyConflictError,
    OrderService,
)


router = APIRouter(tags=["Orders"])


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    order_data: OrderCreate,
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
        return OrderService.create_order(
            db,
            customer_id=current_user.id,
            order_data=order_data,
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
            detail="Order conflicts with existing data.",
        ) from exc


@router.get("/orders/me", response_model=list[OrderResponse])
def get_my_orders(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    return OrderService.get_customer_orders(
        db, customer_id=current_user.id, skip=skip, limit=limit
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_my_order(
    order_id: int,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        return OrderService.get_customer_order(
            db, order_id=order_id, customer_id=current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
def cancel_my_order(
    order_id: int,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        return OrderService.cancel_order(
            db=db, order_id=order_id, customer_id=current_user.id
        )
    except ValueError as exc:
        message = str(exc)
        code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=code, detail=message) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Order cancellation conflicts with an existing transaction.",
        ) from exc


@router.get("/vendor-orders/me", response_model=list[VendorOrderResponse])
def get_my_vendor_orders(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
):
    return OrderService.get_vendor_orders(
        db, vendor_id=current_vendor.id, skip=skip, limit=limit
    )


@router.get("/vendor-orders/{vendor_order_id}", response_model=VendorOrderResponse)
def get_vendor_order(
    vendor_order_id: int,
    current_vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
):
    try:
        return OrderService.get_vendor_order(
            db, vendor_order_id=vendor_order_id, vendor_id=current_vendor.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch(
    "/vendor-orders/{vendor_order_id}/status",
    response_model=VendorOrderResponse,
)
def update_vendor_order_status(
    vendor_order_id: int,
    status_data: VendorOrderStatusUpdate,
    current_vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
):
    try:
        return OrderService.update_vendor_order_status(
            db,
            vendor_order_id=vendor_order_id,
            vendor_id=current_vendor.id,
            new_status=status_data.status,
        )
    except ValueError as exc:
        message = str(exc)
        code = (
            404
            if "not found" in message.lower() or "does not belong" in message.lower()
            else 400
        )
        raise HTTPException(status_code=code, detail=message) from exc
