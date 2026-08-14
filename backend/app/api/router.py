from fastapi import APIRouter

from app.api.v1 import health, diagnosis, devices, users, auth

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["diagnosis"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])