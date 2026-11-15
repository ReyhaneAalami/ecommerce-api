
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.connections.database import get_db
from src.api.dependencies import get_current_vendor
from src.data.models import Vendor
from src.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)
from src.services.product_service import ProductService


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


# Public: List active products
@router.get(
    "",
    response_model=list[ProductResponse],
)
def get_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    try:
        return ProductService.get_products(
            db,
            skip=skip,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# Vendor: List own products
@router.get(
    "/vendor/me",
    response_model=list[ProductResponse],
)
def get_my_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
):
    try:
        return ProductService.get_vendor_products(
            db,
            vendor_id=current_vendor.id,
            skip=skip,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# Vendor: Create product
@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_data: ProductCreate,
    current_vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
):
    try:
        return ProductService.create_product(
            db,
            vendor_id=current_vendor.id,
            product_data=product_data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product slug or SKU already exists.",
        ) from exc


# Public: Get product details
@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    try:
        return ProductService.get_product(
            db,
            product_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# Vendor: Update own product
@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
):
    try:
        return ProductService.update_product(
            db,
            vendor_id=current_vendor.id,
            product_id=product_id,
            update_data=product_data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product update conflicts with existing data.",
        ) from exc


# Vendor: Soft-delete own product
@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
)
def delete_product(
    product_id: int,
    current_vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
):
    try:
        return ProductService.delete_product(
            db,
            vendor_id=current_vendor.id,
            product_id=product_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
