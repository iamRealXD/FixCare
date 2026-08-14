from app.api.v1.health import router as health_router
from app.api.v1.diagnosis import router as diagnosis_router
from app.api.v1.devices import router as devices_router
from app.api.v1.users import router as users_router
from app.api.v1.auth import router as auth_router

__all__ = [
    "health_router",
    "diagnosis_router",
    "devices_router",
    "users_router",
    "auth_router",
]