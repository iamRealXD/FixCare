from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.schemas.diagnosis import (
    DiagnosisRequest,
    DiagnosisResultResponse,
    PossibleCause,
    SafeStep,
    RiskItem,
    FollowUpQuestion,
)


@dataclass
class AIProviderMetadata:
    provider: str
    model: str
    prompt_version: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    success: bool = True
    error_message: str | None = None


class AIProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    async def diagnose(
        self,
        request: DiagnosisRequest,
        diagnosis_id: UUID | None = None,
    ) -> tuple[DiagnosisResultResponse, AIProviderMetadata]:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass