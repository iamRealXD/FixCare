import uuid
from datetime import datetime, timedelta, UTC
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_expiration_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.JWTError:
        return None


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> uuid.UUID:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    payload = decode_access_token(credentials.credentials)

    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    try:
        return uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )