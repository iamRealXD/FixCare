from uuid import UUID
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.models.diagnosis import Diagnosis, DiagnosisResult, DiagnosisFeedback
from app.db.models.device import Device
from app.schemas.diagnosis import DiagnosisStatus
from app.core.logging import get_logger


logger = get_logger(__name__)


class HistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_diagnosis_detail(self, diagnosis_id: UUID, user_id: UUID) -> Diagnosis | None:
        result = await self.db.execute(
            select(Diagnosis)
            .where(Diagnosis.id == diagnosis_id, Diagnosis.user_id == user_id)
            .options(
                selectinload(Diagnosis.messages),
                selectinload(Diagnosis.results),
                selectinload(Diagnosis.feedback),
                selectinload(Diagnosis.ai_logs),
                selectinload(Diagnosis.device),
            )
        )
        return result.scalar_one_or_none()

    async def list_diagnoses(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        status: DiagnosisStatus | None = None,
        device_category: str | None = None,
    ) -> tuple[list[Diagnosis], int]:
        query = select(Diagnosis).where(Diagnosis.user_id == user_id)
        count_query = select(func.count(Diagnosis.id)).where(Diagnosis.user_id == user_id)

        if status:
            query = query.where(Diagnosis.status == status)
            count_query = count_query.where(Diagnosis.status == status)

        if device_category:
            query = query.where(Diagnosis.device_category == device_category)
            count_query = count_query.where(Diagnosis.device_category == device_category)

        query = query.order_by(Diagnosis.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        diagnoses = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return diagnoses, total

    async def get_statistics(self, user_id: UUID) -> dict[str, Any]:
        from sqlalchemy import func

        total_result = await self.db.execute(
            select(func.count(Diagnosis.id)).where(Diagnosis.user_id == user_id)
        )
        total = total_result.scalar() or 0

        completed_result = await self.db.execute(
            select(func.count(Diagnosis.id)).where(
                Diagnosis.user_id == user_id,
                Diagnosis.status == DiagnosisStatus.COMPLETED,
            )
        )
        completed = completed_result.scalar() or 0

        escalated_result = await self.db.execute(
            select(func.count(Diagnosis.id)).where(
                Diagnosis.user_id == user_id,
                Diagnosis.status == DiagnosisStatus.ESCALATED,
            )
        )
        escalated = escalated_result.scalar() or 0

        category_result = await self.db.execute(
            select(Diagnosis.device_category, func.count(Diagnosis.id))
            .where(Diagnosis.user_id == user_id)
            .group_by(Diagnosis.device_category)
        )
        by_category = dict(category_result.all())

        severity_result = await self.db.execute(
            select(Diagnosis.severity, func.count(Diagnosis.id))
            .where(Diagnosis.user_id == user_id)
            .group_by(Diagnosis.severity)
        )
        by_severity = dict(severity_result.all())

        return {
            "total_diagnoses": total,
            "completed": completed,
            "escalated": escalated,
            "by_category": by_category,
            "by_severity": by_severity,
        }