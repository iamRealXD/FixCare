from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.user import UserCreate, LoginRequest, TokenResponse
from app.schemas.common import ErrorResponse
from app.services.user_service import UserService
from app.core.security import create_access_token
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    
    try:
        user = await service.create_user(data)
        access_token = create_access_token({"sub": str(user.id)})
        
        settings = get_settings()
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.jwt_expiration_minutes * 60,
        )
    except ValidationError as e:
        logger.warning("register_validation_error", error=str(e))
        raise HTTPException(status_code=400, detail=e.message)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse},
    },
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    
    user = await service.authenticate(data.email, data.password)
    if not user:
        logger.warning("login_failed", email=data.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token({"sub": str(user.id)})
    
    settings = get_settings()
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_expiration_minutes * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout():
    # Client-side token deletion; server-side would require token blacklist
    return None