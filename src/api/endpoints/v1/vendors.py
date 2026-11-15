from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.connections.database import get_db
from src.api.dependencies import (
    get_current_admin,
    get_current_customer,
    get_current_vendor,
)
from src.data.models import User, Vendor
from src.schemas.vendor import (
    VendorCreate,
    VendorUpdate,
    VendorAdminStatusUpdate,
    VendorResponse,
)
from src.services.vendor_service import VendorService


router = APIRouter(
    prefix="/vendors",
    tags=["Vendors"],
)


@router.post(
    "/register",
    response_model=VendorResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_vendor(
    vendor_data: VendorCreate,
    current_user: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        return VendorService.register_vendor(
            db,
            current_user,
            vendor_data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Store name is already registered.",
        ) from exc


@router.get(
    "/me",
    response_model=VendorResponse,
)
def get_my_vendor(
    current_vendor: Vendor = Depends(get_current_vendor),
):
    return current_vendor


@router.patch(
    "/me",
    response_model=VendorResponse,
)
def update_my_vendor(
    vendor_data: VendorUpdate,
    current_vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
):
    try:
        return VendorService.update_vendor(
            db,
            current_vendor,
            vendor_data,
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
            detail="Store name is already registered.",
        ) from exc


@router.get(
    "/admin/pending",
    response_model=list[VendorResponse],
)
def get_pending_vendors(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return VendorService.get_pending_vendors(db)


@router.patch(
    "/admin/{vendor_id}/review",
    response_model=VendorResponse,
)
def review_vendor(
    vendor_id: int,
    decision_data: VendorAdminStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        return VendorService.review_vendor(
            db,
            vendor_id,
            decision_data.status,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to update vendor status.",
        ) from exc