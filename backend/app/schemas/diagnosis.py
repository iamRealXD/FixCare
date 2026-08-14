from uuid import UUID
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum


class DeviceCategory(str, Enum):
    MOBILE = "mobile"
    LAPTOP = "laptop"
    TV = "tv"


class DiagnosisSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class DiagnosisStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class PossibleCause(BaseModel):
    cause: str
    likelihood: str
    confidence: float = Field(ge=0.0, le=1.0)


class SafeStep(BaseModel):
    step: int
    instruction: str
    purpose: str
    risk: RiskLevel


class RiskItem(BaseModel):
    risk: RiskLevel
    description: str
    action: str


class FollowUpQuestion(BaseModel):
    question: str
    options: list[str] | None = None


class DiagnosisRequest(BaseModel):
    device_category: DeviceCategory
    problem_description: str = Field(min_length=10, max_length=5000)
    device_id: UUID | None = None
    brand: str | None = None
    model: str | None = None
    follow_up_answers: list[dict[str, str]] | None = None


class DiagnosisResultResponse(BaseModel):
    device: dict[str, Any]
    problem: dict[str, Any]
    possible_causes: list[PossibleCause]
    safe_steps: list[SafeStep]
    risks: list[RiskItem]
    technician_required: bool
    technician_reason: str | None
    follow_up_questions: list[FollowUpQuestion]
    disclaimer: str


class DiagnosisResponse(BaseModel):
    id: UUID
    status: DiagnosisStatus
    device_category: DeviceCategory
    problem_summary: str
    severity: DiagnosisSeverity
    technician_required: bool
    technician_reason: str | None
    result: DiagnosisResultResponse | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class DiagnosisListItem(BaseModel):
    id: UUID
    device_category: DeviceCategory
    problem_summary: str
    severity: DiagnosisSeverity
    status: DiagnosisStatus
    technician_required: bool
    created_at: datetime
    completed_at: datetime | None = None


class DiagnosisFeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = None
    was_helpful: bool | None = None
    resolved: bool | None = None


class DiagnosisFeedbackResponse(BaseModel):
    id: UUID
    diagnosis_id: UUID
    rating: int
    comment: str | None
    was_helpful: bool | None
    resolved: bool | None
    created_at: datetime


class AIRequestLogResponse(BaseModel):
    id: UUID
    provider: str
    model: str
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost: float | None
    success: bool
    error_message: str | None
    created_at: datetime