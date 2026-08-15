import json
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.ai.factory import AIProviderFactory
from app.services.ai.base import AIProvider, AIProviderMetadata
from app.services.safety_service import safety_service, SafetyScreeningResult
from app.schemas.diagnosis import (
    DiagnosisRequest,
    DiagnosisResultResponse,
    DiagnosisSeverity,
    DiagnosisStatus,
    FollowUpAnswer,
)
from app.db.models.diagnosis import (
    Diagnosis,
    DiagnosisMessage,
    DiagnosisResult,
    AIRequestLog,
    RiskLevel,
)
from app.db.models.user import User
from app.db.models.device import Device
from app.core.logging import get_logger
from app.core.exceptions import (
    AIProviderError,
    AIResponseValidationError,
    SafetyEscalationError,
    ValidationError,
)


logger = get_logger(__name__)


class DiagnosisService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_provider: AIProvider = AIProviderFactory.get_provider()

    async def create_diagnosis(
        self,
        user_id: UUID,
        request: DiagnosisRequest,
    ) -> Diagnosis:
        device = None
        if request.device_id:
            result = await self.db.execute(
                select(Device).where(Device.id == request.device_id, Device.user_id == user_id)
            )
            device = result.scalar_one_or_none()
            if not device:
                raise ValidationError("Device not found or access denied")

        screening = safety_service.screen_user_input(
            request.problem_description,
            request.device_category.value,
        )

        diagnosis = Diagnosis(
            user_id=user_id,
            device_id=device.id if device else None,
            device_category=request.device_category.value,
            device_brand=request.brand,
            device_model=request.model,
            problem_summary=request.problem_description[:500],
            severity=self._map_severity(screening.risk_level),
            status=DiagnosisStatus.PENDING,
            technician_required=screening.technician_required,
            technician_reason=screening.technician_reason,
        )

        self.db.add(diagnosis)
        await self.db.flush()

        message = DiagnosisMessage(
            diagnosis_id=diagnosis.id,
            role="user",
            content=request.problem_description,
            sequence=0,
        )
        self.db.add(message)

        if request.follow_up_answers:
            for i, answer in enumerate(request.follow_up_answers, 1):
                msg = DiagnosisMessage(
                    diagnosis_id=diagnosis.id,
                    role="user",
                    content=json.dumps(answer.model_dump()),
                    sequence=i,
                )
                self.db.add(msg)

        await self.db.commit()
        await self.db.refresh(diagnosis)

        return diagnosis

    async def run_diagnosis(self, diagnosis_id: UUID) -> Diagnosis:
        result = await self.db.execute(
            select(Diagnosis).where(Diagnosis.id == diagnosis_id)
        )
        diagnosis = result.scalar_one_or_none()
        if not diagnosis:
            raise ValidationError("Diagnosis not found")

        if diagnosis.status != DiagnosisStatus.PENDING:
            logger.warning("diagnosis_not_pending", diagnosis_id=str(diagnosis_id), status=diagnosis.status.value)
            return diagnosis

        diagnosis.status = DiagnosisStatus.IN_PROGRESS
        await self.db.commit()

        try:
            request = await self._build_request_from_context(diagnosis)
            safety_context = "\n".join(
                [
                    request.problem_description,
                    *[
                        f"{answer.question}: {answer.answer}"
                        for answer in request.follow_up_answers or []
                    ],
                ]
            )
            screening = safety_service.screen_user_input(
                safety_context,
                diagnosis.device_category,
            )
            diagnosis.severity = self._map_severity(screening.risk_level)

            ai_result, metadata = await self.ai_provider.diagnose(request, diagnosis_id)

            valid, errors = safety_service.validate_ai_response(ai_result)
            if not valid:
                logger.error("ai_response_validation_failed", errors=errors, diagnosis_id=str(diagnosis_id))
                raise AIResponseValidationError("AI response failed safety validation", details={"errors": errors})

            diagnosis.status = DiagnosisStatus.COMPLETED
            diagnosis.technician_required = (
                screening.technician_required or ai_result.technician_required
            )
            diagnosis.technician_reason = (
                screening.technician_reason
                if screening.technician_required
                else ai_result.technician_reason
            )
            diagnosis.ai_provider = metadata.provider
            diagnosis.ai_model = metadata.model
            diagnosis.ai_latency_ms = metadata.latency_ms
            diagnosis.ai_input_tokens = metadata.input_tokens
            diagnosis.ai_output_tokens = metadata.output_tokens
            diagnosis.ai_estimated_cost = metadata.estimated_cost
            diagnosis.completed_at = await self._get_utc_now()

            result_obj = DiagnosisResult(
                diagnosis_id=diagnosis.id,
                possible_causes=[c.model_dump() for c in ai_result.possible_causes],
                safe_steps=[s.model_dump() for s in ai_result.safe_steps],
                risks=[r.model_dump() for r in ai_result.risks],
                follow_up_questions=[q.model_dump() for q in ai_result.follow_up_questions],
                disclaimer=ai_result.disclaimer,
            )
            self.db.add(result_obj)

            if diagnosis.technician_required:
                diagnosis.status = DiagnosisStatus.ESCALATED

            ai_log = AIRequestLog(
                diagnosis_id=diagnosis.id,
                provider=metadata.provider,
                model=metadata.model,
                prompt_version=metadata.prompt_version,
                request_payload=request.model_dump(mode="json"),
                response_payload=ai_result.model_dump(mode="json"),
                latency_ms=metadata.latency_ms,
                input_tokens=metadata.input_tokens,
                output_tokens=metadata.output_tokens,
                estimated_cost=metadata.estimated_cost,
                success=metadata.success,
                error_message=metadata.error_message,
            )
            self.db.add(ai_log)

            await self.db.commit()
            await self.db.refresh(diagnosis)

            logger.info("diagnosis_completed", diagnosis_id=str(diagnosis_id), provider=metadata.provider)
            return diagnosis

        except Exception as e:
            diagnosis.status = DiagnosisStatus.FAILED
            await self.db.commit()
            logger.error("diagnosis_failed", diagnosis_id=str(diagnosis_id), error=str(e))
            raise

    async def submit_follow_up_answers(
        self,
        diagnosis_id: UUID,
        user_id: UUID,
        answers: list[FollowUpAnswer],
    ) -> Diagnosis:
        result = await self.db.execute(
            select(Diagnosis).where(
                Diagnosis.id == diagnosis_id,
                Diagnosis.user_id == user_id,
            )
        )
        diagnosis = result.scalar_one_or_none()
        if not diagnosis:
            raise ValidationError("Diagnosis not found")

        result_rows = await self.db.execute(
            select(DiagnosisResult).where(DiagnosisResult.diagnosis_id == diagnosis_id)
        )
        for result_row in result_rows.scalars():
            await self.db.delete(result_row)

        message_rows = await self.db.execute(
            select(DiagnosisMessage).where(
                DiagnosisMessage.diagnosis_id == diagnosis_id,
                DiagnosisMessage.sequence > 0,
            )
        )
        for message in message_rows.scalars():
            await self.db.delete(message)

        for sequence, answer in enumerate(answers, 1):
            self.db.add(
                DiagnosisMessage(
                    diagnosis_id=diagnosis_id,
                    role="user",
                    content=json.dumps(answer.model_dump()),
                    sequence=sequence,
                )
            )

        diagnosis.status = DiagnosisStatus.PENDING
        diagnosis.completed_at = None
        diagnosis.technician_required = False
        diagnosis.technician_reason = None
        await self.db.commit()

        return await self.run_diagnosis(diagnosis_id)

    async def _build_request_from_context(
        self,
        diagnosis: Diagnosis,
    ) -> DiagnosisRequest:
        result = await self.db.execute(
            select(DiagnosisMessage)
            .where(DiagnosisMessage.diagnosis_id == diagnosis.id)
            .order_by(DiagnosisMessage.sequence.asc())
        )
        messages = list(result.scalars())
        original_problem = next(
            (
                message.content
                for message in messages
                if message.sequence == 0
            ),
            diagnosis.problem_summary,
        )
        follow_up_answers = [
            answer
            for message in messages
            if message.sequence > 0
            for answer in [self._parse_follow_up_answer(message.content)]
            if answer is not None
        ]

        return DiagnosisRequest(
            device_category=diagnosis.device_category,
            problem_description=original_problem,
            device_id=diagnosis.device_id,
            brand=diagnosis.device_brand,
            model=diagnosis.device_model,
            follow_up_answers=follow_up_answers or None,
        )

    def _parse_follow_up_answer(self, content: str) -> FollowUpAnswer | None:
        try:
            data = json.loads(content)
            return FollowUpAnswer.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            pass

        if content.startswith("Q: ") and "\nA: " in content:
            question, answer = content[3:].split("\nA: ", maxsplit=1)
            try:
                return FollowUpAnswer(question=question, answer=answer)
            except ValueError:
                return None
        return None

    async def get_diagnosis(self, diagnosis_id: UUID, user_id: UUID) -> Diagnosis | None:
        result = await self.db.execute(
            select(Diagnosis).where(Diagnosis.id == diagnosis_id, Diagnosis.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_diagnoses(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Diagnosis]:
        result = await self.db.execute(
            select(Diagnosis)
            .where(Diagnosis.user_id == user_id)
            .order_by(Diagnosis.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def add_feedback(
        self,
        diagnosis_id: UUID,
        user_id: UUID,
        rating: int,
        comment: str | None = None,
        was_helpful: bool | None = None,
        resolved: bool | None = None,
    ) -> None:
        from app.db.models.diagnosis import DiagnosisFeedback

        result = await self.db.execute(
            select(Diagnosis).where(Diagnosis.id == diagnosis_id, Diagnosis.user_id == user_id)
        )
        diagnosis = result.scalar_one_or_none()
        if not diagnosis:
            raise ValidationError("Diagnosis not found")

        feedback = DiagnosisFeedback(
            diagnosis_id=diagnosis_id,
            user_id=user_id,
            rating=rating,
            comment=comment,
            was_helpful=was_helpful,
            resolved=resolved,
        )
        self.db.add(feedback)
        await self.db.commit()

    def _map_severity(self, risk_level: RiskLevel) -> DiagnosisSeverity:
        mapping = {
            RiskLevel.SAFE: DiagnosisSeverity.LOW,
            RiskLevel.LOW: DiagnosisSeverity.LOW,
            RiskLevel.MODERATE: DiagnosisSeverity.MEDIUM,
            RiskLevel.HIGH: DiagnosisSeverity.HIGH,
            RiskLevel.CRITICAL: DiagnosisSeverity.CRITICAL,
        }
        return mapping.get(risk_level, DiagnosisSeverity.MEDIUM)

    async def _get_utc_now(self):
        from datetime import datetime, UTC
        return datetime.now(UTC)
