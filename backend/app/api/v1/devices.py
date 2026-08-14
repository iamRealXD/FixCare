import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.device import DeviceCreate, DeviceUpdate, DeviceResponse, DeviceListResponse
from app.schemas.common import ErrorResponse
from app.services.device_service import DeviceService
from app.core.exceptions import ValidationError, NotFoundError
from app.core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter()


def get_request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID", str(uuid.uuid4()))


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


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def create_device(
    data: DeviceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id(request)
    service = DeviceService(db)
    
    try:
        device = await service.create_device(user_id, data)
        return DeviceResponse.model_validate(device)
    except ValidationError as e:
        logger.warning("device_create_validation_error", request_id=get_request_id(request), error=str(e))
        raise HTTPException(status_code=400, detail=e.message)


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_device(
    device_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id(request)
    service = DeviceService(db)
    
    device = await service.get_device(device_id, user_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return DeviceResponse.model_validate(device)


@router.get(
    "",
    response_model=DeviceListResponse,
    responses={401: {"model": ErrorResponse}},
)
async def list_devices(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id(request)
    service = DeviceService(db)
    
    from app.schemas.diagnosis import DeviceCategory
    cat = DeviceCategory(category) if category else None
    
    devices, total = await service.list_devices(user_id, limit=limit, offset=offset, category=cat)
    
    return DeviceListResponse(
        devices=[DeviceResponse.model_validate(d) for d in devices],
        total=total,
    )


@router.patch(
    "/{device_id}",
    response_model=DeviceResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def update_device(
    device_id: uuid.UUID,
    data: DeviceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id(request)
    service = DeviceService(db)
    
    try:
        device = await service.update_device(device_id, user_id, data)
        return DeviceResponse.model_validate(device)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def delete_device(
    device_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id(request)
    service = DeviceService(db)
    
    try:
        await service.delete_device(device_id, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)