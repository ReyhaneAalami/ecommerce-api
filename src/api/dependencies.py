from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.connections.database import get_db
from src.data.models import User
from src.repositories.user_repository import UserRepository
from src.utils.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> User:
    """Get the authenticated user from the JWT access token."""

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    user_id = decode_access_token(credentials.credentials)

    if user_id is None:
        raise unauthorized

    user = UserRepository.get_by_id(db, user_id)

    if user is None or not user.is_active:
        raise unauthorized

    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Allow only users with the admin role."""

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )

    return current_user


def get_current_customer(
    current_user: User = Depends(get_current_user),
) -> User:
    """Allow only active customer accounts."""

    if current_user.role != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation is available to customers only.",
        )

    return current_user


def get_current_vendor(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the vendor profile belonging to the authenticated user."""

    if current_user.role != "vendor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account does not belong to a vendor.",
        )

    from src.repositories.vendor_repository import VendorRepository

    vendor = VendorRepository.get_by_user_id(db, current_user.id)

    if vendor is None or not vendor.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active vendor profile not found.",
        )

    return vendor