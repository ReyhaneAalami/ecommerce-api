
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from src.config import settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a plain password against its hash."""
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
        "type": "access",
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> int | None:
    """Decode a JWT and return its user ID."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        if payload.get("type") != "access":
            return None

        user_id = int(payload["sub"])

        if user_id <= 0:
            return None

        return user_id

    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        return None
