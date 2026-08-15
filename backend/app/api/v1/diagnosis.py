import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user_id
from app.db.database import get_db
from app.schemas.diagnosis import (
    DiagnosisRequest,
    DiagnosisFollowUpRequest,
    DiagnosisResponse,
    DiagnosisListItem,
    DiagnosisFeedbackRequest,
    DiagnosisFeedbackResponse,
)
from app.schemas.common import ErrorResponse
from app.services.diagnosis_service import DiagnosisService
from app.services.history_service import HistoryService
from app.core.exceptions import (
    ValidationError,
    AIProviderError,
    AIResponseValidationError,
    SafetyEscalationError,
    NotFoundError,
)
from app.core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter()


def get_request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID", str(uuid.uuid4()))


@router.post(
    "",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def create_diagnosis(
    request: DiagnosisRequest,
    http_request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    request_id = get_request_id(http_request)
    
    

    service = DiagnosisService(db)
    try:
        diagnosis = await service.create_diagnosis(user_id, request)
        diagnosis = await service.run_diagnosis(diagnosis.id)
        
        await db.refresh(diagnosis, ["results"])

        result = await _build_diagnosis_response(diagnosis, db)
        return result

    except ValidationError as e:
        logger.warning("diagnosis_validation_error", request_id=request_id, error=str(e))
        raise HTTPException(status_code=400, detail=e.message)
    except SafetyEscalationError as e:
        logger.warning("safety_escalation", request_id=request_id, details=e.details)
        raise HTTPException(status_code=400, detail=e.message)
    except AIProviderError as e:
        logger.error("ai_provider_error", request_id=request_id, error=str(e))
        raise HTTPException(status_code=502, detail="AI provider error")
    except AIResponseValidationError as e:
        logger.error("ai_response_validation_error", request_id=request_id, error=str(e))
        raise HTTPException(status_code=502, detail="Invalid AI response")
    except Exception as e:
        logger.error("diagnosis_unexpected_error", request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/{diagnosis_id}",
    response_model=DiagnosisResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_diagnosis(
    diagnosis_id: uuid.UUID,
    http_request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    request_id = get_request_id(http_request)
    
    

    service = HistoryService(db)
    diagnosis = await service.get_diagnosis_detail(diagnosis_id, user_id)
    
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not found")

    return await _build_diagnosis_response(diagnosis, db)


@router.post(
    "/{diagnosis_id}/follow-up",
    response_model=DiagnosisResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def submit_follow_up_answers(
    diagnosis_id: uuid.UUID,
    data: DiagnosisFollowUpRequest,
    http_request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    request_id = get_request_id(http_request)
    service = DiagnosisService(db)

    try:
        diagnosis = await service.submit_follow_up_answers(
            diagnosis_id,
            user_id,
            data.answers,
        )
        await db.refresh(diagnosis, ["results"])
        return await _build_diagnosis_response(diagnosis, db)
    except ValidationError as e:
        logger.warning(
            "diagnosis_follow_up_validation_error",
            request_id=request_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=e.message)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AIProviderError as e:
        logger.error("follow_up_ai_provider_error", request_id=request_id, error=str(e))
        raise HTTPException(status_code=502, detail="AI provider error")
    except AIResponseValidationError as e:
        logger.error("follow_up_ai_response_invalid", request_id=request_id, error=str(e))
        raise HTTPException(status_code=502, detail="Invalid AI response")


@router.get(
    "",
    response_model=list[DiagnosisListItem],
    responses={401: {"model": ErrorResponse}},
)
async def list_diagnoses(
    http_request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    

    service = HistoryService(db)
    diagnoses = await service.list_diagnoses(user_id, limit=limit, offset=offset)

    return [
        DiagnosisListItem(
            id=d.id,
            device_category=d.device_category,
            problem_summary=d.problem_summary,
            severity=d.severity,
            status=d.status,
            technician_required=d.technician_required,
            created_at=d.created_at,
            completed_at=d.completed_at,
        )
        for d in diagnoses
    ]


@router.post(
    "/{diagnosis_id}/feedback",
    response_model=DiagnosisFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def create_feedback(
    diagnosis_id: uuid.UUID,
    feedback: DiagnosisFeedbackRequest,
    http_request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    

    service = DiagnosisService(db)
    try:
        await service.add_feedback(
            diagnosis_id,
            user_id,
            feedback.rating,
            feedback.comment,
            feedback.was_helpful,
            feedback.resolved,
        )
        
        from app.db.models.diagnosis import DiagnosisFeedback
        from sqlalchemy import select
        result = await db.execute(
            select(DiagnosisFeedback)
            .where(DiagnosisFeedback.diagnosis_id == diagnosis_id, DiagnosisFeedback.user_id == user_id)
            .order_by(DiagnosisFeedback.created_at.desc())
        )
        fb = result.scalar_one()
        
        return DiagnosisFeedbackResponse(
            id=fb.id,
            diagnosis_id=fb.diagnosis_id,
            rating=fb.rating,
            comment=fb.comment,
            was_helpful=fb.was_helpful,
            resolved=fb.resolved,
            created_at=fb.created_at,
        )
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=e.message)


async def _build_diagnosis_response(diagnosis, db: AsyncSession) -> DiagnosisResponse:
    from app.schemas.diagnosis import (
        DiagnosisResultResponse,
        PossibleCause,
        SafeStep,
        RiskItem,
        FollowUpQuestion,
        RiskLevel,
        DiagnosisSeverity,
        DiagnosisStatus,
    )
    from app.db.models.diagnosis import DiagnosisResult

    result = None
    if diagnosis.results:
        r = diagnosis.results[0]
        result = DiagnosisResultResponse(
            device={
                "category": diagnosis.device_category,
                "brand": diagnosis.device_brand,
                "model": diagnosis.device_model,
            },
            problem={
                "summary": diagnosis.problem_summary,
                "severity": diagnosis.severity,
            },
            possible_causes=[PossibleCause(**c) for c in r.possible_causes],
            safe_steps=[SafeStep(**s) for s in r.safe_steps],
            risks=[RiskItem(**rk) for rk in r.risks],
            technician_required=diagnosis.technician_required,
            technician_reason=diagnosis.technician_reason,
            follow_up_questions=[FollowUpQuestion(**q) for q in r.follow_up_questions],
            disclaimer=r.disclaimer,
        )

    return DiagnosisResponse(
        id=diagnosis.id,
        status=diagnosis.status,
        device_category=diagnosis.device_category,
        problem_summary=diagnosis.problem_summary,
        severity=diagnosis.severity,
        technician_required=diagnosis.technician_required,
        technician_reason=diagnosis.technician_reason,
        result=result,
        created_at=diagnosis.created_at,
        updated_at=diagnosis.updated_at,
        completed_at=diagnosis.completed_at,
    )
