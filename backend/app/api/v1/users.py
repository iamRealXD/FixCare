import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.common import ErrorResponse
from app.services.user_service import UserService
from app.core.exceptions import ValidationError, NotFoundError
from app.core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter()


def get_user_id(request: Request) -> uuid.UUID:
    from app.core.security import decode_access_token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return uuid.UUID(payload["sub"])


@router.get(
    "/me",
    response_model=UserResponse,
    responses={401: {"model": ErrorResponse}},
)
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id(request)
    service = UserService(db)
    
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse.model_validate(user)


@router.patch(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def update_current_user(
    data: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id(request)
    service = UserService(db)
    
    try:
        user = await service.update_user(user_id, data)
        return UserResponse.model_validate(user)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)