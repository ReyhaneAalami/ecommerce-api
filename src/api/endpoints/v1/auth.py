
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.connections.database import get_db
from src.schemas.auth import AuthResponse, LoginRequest
from src.schemas.user import UserCreate, UserResponse
from src.services.auth_service import AuthService
from src.utils.security import create_access_token


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    """Register a new customer account."""

    try:
        user = AuthService.register(db, user_data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ایمیل یا شماره تلفن قبلاً ثبت شده است.",
        ) from exc

    token = create_access_token(user.id)

    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    """Authenticate a user and return an access token."""

    user = AuthService.authenticate(
        db,
        email=str(login_data.email),
        password=login_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ایمیل یا رمز عبور اشتباه است.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)

    return AuthResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )
