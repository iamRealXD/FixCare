import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.schemas.common import ErrorResponse
from app.services.user_service import UserService
from app.core.exceptions import ValidationError, NotFoundError
from app.core.logging import get_logger
from app.core.security import get_current_user_id

logger = get_logger(__name__)
router = APIRouter()





@router.get(
    "/me",
    response_model=UserResponse,
    responses={401: {"model": ErrorResponse}},
)
async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
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
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    
    service = UserService(db)
    
    try:
        user = await service.update_user(user_id, data)
        return UserResponse.model_validate(user)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)