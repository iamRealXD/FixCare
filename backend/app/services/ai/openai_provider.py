import asyncio
import json
import time
from uuid import UUID
from typing import Any

import openai
from openai import AsyncOpenAI

from app.services.ai.base import AIProvider, AIProviderMetadata
from app.schemas.diagnosis import (
    DiagnosisRequest,
    DiagnosisResultResponse,
    PossibleCause,
    SafeStep,
    RiskItem,
    FollowUpQuestion,
    RiskLevel,
    DeviceCategory,
    DiagnosisSeverity,
)
from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)

DIAGNOSIS_SYSTEM_PROMPT = """You are FixCare, a structured device troubleshooting assistant. Your role is to help users understand their device problems and safely determine the next best action.

CRITICAL RULES:
1. NEVER claim a diagnosis is confirmed. Always communicate uncertainty.
2. NEVER instruct users to open mains-powered equipment, handle high-voltage components, bypass safety mechanisms, or perform dangerous repairs.
3. ALWAYS prioritize safety. If dangerous conditions are suspected (swollen battery, burning smell, smoke, sparks, water damage, exposed wiring), escalate immediately.
4. Provide structured, actionable troubleshooting steps that are safe for consumers.
5. Clearly distinguish between: likely causes, possible causes, confirmed information, assumptions, and recommended actions.
6. Include a disclaimer that this is troubleshooting guidance, not a confirmed hardware diagnosis.

OUTPUT FORMAT: Return ONLY valid JSON matching this schema:
{
  "device": {"category": "mobile|laptop|tv", "brand": "string|null", "model": "string|null"},
  "problem": {"summary": "string", "severity": "low|medium|high|critical"},
  "possible_causes": [{"cause": "string", "likelihood": "high|medium|possible|unlikely", "confidence": 0.0-1.0}],
  "safe_steps": [{"step": 1, "instruction": "string", "purpose": "string", "risk": "safe|low|moderate|high|critical"}],
  "risks": [{"risk": "safe|low|moderate|high|critical", "description": "string", "action": "string"}],
  "technician_required": boolean,
  "technician_reason": "string|null",
  "follow_up_questions": [{"question": "string", "options": ["string"]}],
  "disclaimer": "string"
}"""

DIAGNOSIS_FOLLOWUP_PROMPT = """You are FixCare continuing a diagnosis conversation. The user has answered follow-up questions. Refine your diagnosis based on the new information.

Return the SAME JSON schema as the initial diagnosis."""


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self._model = "gpt-4o-mini"

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def diagnose(
        self,
        request: DiagnosisRequest,
        diagnosis_id: UUID | None = None,
    ) -> tuple[DiagnosisResultResponse, AIProviderMetadata]:
        if not self.client:
            raise ValueError("OpenAI API key not configured")

        start_time = time.time()
        
        messages = [
            {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
            {"role": "user", "content": self._build_user_prompt(request)},
        ]

        if request.follow_up_answers:
            followup_content = self._build_followup_prompt(request)
            messages.append({"role": "user", "content": followup_content})

        try:
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"},
                timeout=30.0,
            )

            latency_ms = int((time.time() - start_time) * 1000)
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")

            parsed = json.loads(content)
            result = self._parse_response(parsed)

            metadata = AIProviderMetadata(
                provider=self.provider_name,
                model=self.model_name,
                prompt_version="v1",
                latency_ms=latency_ms,
                input_tokens=response.usage.prompt_tokens if response.usage else None,
                output_tokens=response.usage.completion_tokens if response.usage else None,
                estimated_cost=self._estimate_cost(response.usage) if response.usage else None,
                success=True,
            )

            return result, metadata

        except openai.APITimeoutError as e:
            logger.error("openai_timeout", error=str(e))
            raise
        except openai.RateLimitError as e:
            logger.error("openai_rate_limit", error=str(e))
            raise
        except openai.APIError as e:
            logger.error("openai_api_error", error=str(e))
            raise
        except json.JSONDecodeError as e:
            logger.error("openai_json_decode_error", error=str(e), content=content[:500] if content else None)
            raise
        except Exception as e:
            logger.error("openai_unexpected_error", error=str(e))
            raise

    async def health_check(self) -> bool:
        if not self.client:
            return False
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False

    def _build_user_prompt(self, request: DiagnosisRequest) -> str:
        return f"""Device Category: {request.device_category.value}
Problem Description: {request.problem_description}
Brand: {request.brand or 'Unknown'}
Model: {request.model or 'Unknown'}

Please provide a structured diagnosis following the JSON schema."""

    def _build_followup_prompt(self, request: DiagnosisRequest) -> str:
        answers = "\n".join([f"Q: {a.get('question', '')}\nA: {a.get('answer', '')}" for a in request.follow_up_answers])
        return f"Follow-up answers:\n{answers}\n\nPlease refine your diagnosis based on this additional information."

    def _parse_response(self, data: dict) -> DiagnosisResultResponse:
        possible_causes = [
            PossibleCause(
                cause=c["cause"],
                likelihood=c["likelihood"],
                confidence=float(c["confidence"]),
            )
            for c in data.get("possible_causes", [])
        ]

        safe_steps = [
            SafeStep(
                step=s["step"],
                instruction=s["instruction"],
                purpose=s["purpose"],
                risk=RiskLevel(s["risk"]),
            )
            for s in data.get("safe_steps", [])
        ]

        risks = [
            RiskItem(
                risk=RiskLevel(r["risk"]),
                description=r["description"],
                action=r["action"],
            )
            for r in data.get("risks", [])
        ]

        follow_up_questions = [
            FollowUpQuestion(
                question=q["question"],
                options=q.get("options"),
            )
            for q in data.get("follow_up_questions", [])
        ]

        return DiagnosisResultResponse(
            device=data.get("device", {}),
            problem=data.get("problem", {}),
            possible_causes=possible_causes,
            safe_steps=safe_steps,
            risks=risks,
            technician_required=data.get("technician_required", False),
            technician_reason=data.get("technician_reason"),
            follow_up_questions=follow_up_questions,
            disclaimer=data.get("disclaimer", "This is troubleshooting guidance, not a confirmed hardware diagnosis."),
        )

    def _estimate_cost(self, usage: Any) -> float:
        if not usage:
            return 0.0
        input_cost = (usage.prompt_tokens / 1_000_000) * 0.15
        output_cost = (usage.completion_tokens / 1_000_000) * 0.60
        return round(input_cost + output_cost, 6)