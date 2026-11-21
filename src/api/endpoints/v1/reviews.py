from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_admin, get_current_customer
from src.connections.database import get_db
from src.data.models import User
from src.schemas.review import ReviewCreate, ReviewModeration, ReviewResponse, ReviewAdminResponse, ReviewAdminListResponse, RatingSummary, ReviewListResponse
from src.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Product Reviews"])


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(data: ReviewCreate, user: User = Depends(get_current_customer), db: Session = Depends(get_db)):
    try:
        return ReviewService.create(db, customer_id=user.id, data=data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A review already exists for this product or purchase.") from exc


@router.get("/products/{product_id}", response_model=ReviewListResponse)
def list_product_reviews(product_id: int, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    try:
        return ReviewService.list_public(db, product_id, skip, limit)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/products/{product_id}/summary", response_model=RatingSummary)
def product_rating_summary(product_id: int, db: Session = Depends(get_db)):
    try:
        return ReviewService.summary(db, product_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/me", response_model=ReviewListResponse)
def my_reviews(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), user: User = Depends(get_current_customer), db: Session = Depends(get_db)):
    return ReviewService.list_mine(db, user.id, skip, limit)


@router.get("/admin/pending", response_model=ReviewAdminListResponse)
def pending_reviews(skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return ReviewService.list_pending(db, skip, limit)


@router.patch("/admin/{review_id}/moderate", response_model=ReviewAdminResponse)
def moderate_review(review_id: int, data: ReviewModeration, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    try:
        return ReviewService.moderate(db, review_id, admin.id, data.status, data.moderation_note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
