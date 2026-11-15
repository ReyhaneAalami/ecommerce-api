from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.connections.database import get_db
from src.data.models import User
from src.api.dependencies import get_current_admin
from src.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
)
from src.services.category_service import CategoryService


router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=list[CategoryResponse],
)
def get_categories(
    db: Session = Depends(get_db),
):
    return CategoryService.get_categories(db)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    try:
        return CategoryService.get_category(db, category_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        return CategoryService.create_category(
            db,
            category_data.model_dump(),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name or slug already exists.",
        )


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
)
def update_category(
    category_id: int,
    update_data: CategoryUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        return CategoryService.update_category(
            db,
            category_id,
            update_data.model_dump(exclude_unset=True),
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name or slug already exists.",
        )