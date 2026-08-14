from uuid import UUID
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


class DeviceCategory(str, Enum):
    MOBILE = "mobile"
    LAPTOP = "laptop"
    TV = "tv"


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: DeviceCategory
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    purchase_date: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: DeviceCategory | None = None
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    purchase_date: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)


class DeviceResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    category: DeviceCategory
    brand: str | None
    model: str | None
    serial_number: str | None
    purchase_date: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceListResponse(BaseModel):
    devices: list[DeviceResponse]
    total: int