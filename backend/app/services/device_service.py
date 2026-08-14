from uuid import UUID
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.models.device import Device, DeviceCategory
from app.db.models.diagnosis import Diagnosis
from app.schemas.device import DeviceCreate, DeviceUpdate
from app.core.logging import get_logger
from app.core.exceptions import ValidationError, NotFoundError


logger = get_logger(__name__)


class DeviceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_device(self, user_id: UUID, data: DeviceCreate) -> Device:
        device = Device(
            user_id=user_id,
            name=data.name,
            category=data.category,
            brand=data.brand,
            model=data.model,
            serial_number=data.serial_number,
            purchase_date=data.purchase_date,
            notes=data.notes,
        )
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)
        logger.info("device_created", device_id=str(device.id), user_id=str(user_id))
        return device

    async def get_device(self, device_id: UUID, user_id: UUID) -> Device | None:
        result = await self.db.execute(
            select(Device)
            .where(Device.id == device_id, Device.user_id == user_id)
            .options(selectinload(Device.diagnoses))
        )
        return result.scalar_one_or_none()

    async def list_devices(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        category: DeviceCategory | None = None,
    ) -> tuple[list[Device], int]:
        query = select(Device).where(Device.user_id == user_id)
        count_query = select(func.count(Device.id)).where(Device.user_id == user_id)

        if category:
            query = query.where(Device.category == category)
            count_query = count_query.where(Device.category == category)

        query = query.order_by(Device.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        devices = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return devices, total

    async def update_device(self, device_id: UUID, user_id: UUID, data: DeviceUpdate) -> Device:
        device = await self.get_device(device_id, user_id)
        if not device:
            raise NotFoundError("Device", str(device_id))

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(device, field, value)

        await self.db.commit()
        await self.db.refresh(device)
        logger.info("device_updated", device_id=str(device_id))
        return device

    async def delete_device(self, device_id: UUID, user_id: UUID) -> None:
        device = await self.get_device(device_id, user_id)
        if not device:
            raise NotFoundError("Device", str(device_id))

        await self.db.delete(device)
        await self.db.commit()
        logger.info("device_deleted", device_id=str(device_id))

    async def get_device_with_diagnoses(self, device_id: UUID, user_id: UUID) -> Device | None:
        result = await self.db.execute(
            select(Device)
            .where(Device.id == device_id, Device.user_id == user_id)
            .options(selectinload(Device.diagnoses))
        )
        return result.scalar_one_or_none()