import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.mock_provider import MockAIProvider
from app.schemas.diagnosis import (
    DiagnosisRequest,
    DeviceCategory,
    RiskLevel,
)


class TestMockAIProvider:
    @pytest.fixture
    def provider(self):
        return MockAIProvider()

    @pytest.fixture
    def sample_request(self):
        return DiagnosisRequest(
            device_category=DeviceCategory.LAPTOP,
            problem_description="Laptop turns on but screen stays black",
        )

    @pytest.mark.asyncio
    async def test_diagnose_returns_valid_result(self, provider, sample_request):
        result, metadata = await provider.diagnose(sample_request)

        assert result is not None
        assert result.device["category"] == "laptop"
        assert result.problem["summary"] == sample_request.problem_description[:200]
        assert len(result.possible_causes) > 0
        assert len(result.safe_steps) > 0
        assert len(result.risks) > 0
        assert result.disclaimer is not None
        assert "troubleshooting guidance" in result.disclaimer.lower()

    @pytest.mark.asyncio
    async def test_diagnose_metadata(self, provider, sample_request):
        result, metadata = await provider.diagnose(sample_request)

        assert metadata.provider == "mock"
        assert metadata.model == "mock-diagnosis-v1"
        assert metadata.latency_ms > 0
        assert metadata.success is True

    @pytest.mark.asyncio
    async def test_diagnose_laptop_category(self, provider):
        request = DiagnosisRequest(
            device_category=DeviceCategory.LAPTOP,
            problem_description="Laptop won't turn on at all",
        )
        result, _ = await provider.diagnose(request)

        assert result.device["category"] == "laptop"
        causes_text = " ".join([c.cause.lower() for c in result.possible_causes])
        assert any(kw in causes_text for kw in ["power", "battery", "display", "ram", "motherboard"])

    @pytest.mark.asyncio
    async def test_diagnose_mobile_category(self, provider):
        request = DiagnosisRequest(
            device_category=DeviceCategory.MOBILE,
            problem_description="Phone screen is black",
        )
        result, _ = await provider.diagnose(request)

        assert result.device["category"] == "mobile"

    @pytest.mark.asyncio
    async def test_diagnose_tv_category(self, provider):
        request = DiagnosisRequest(
            device_category=DeviceCategory.TV,
            problem_description="TV has no picture",
        )
        result, _ = await provider.diagnose(request)

        assert result.device["category"] == "tv"

    @pytest.mark.asyncio
    async def test_safety_escalation_swollen_battery(self, provider):
        request = DiagnosisRequest(
            device_category=DeviceCategory.MOBILE,
            problem_description="Phone has swollen battery",
        )
        result, _ = await provider.diagnose(request)

        assert result.technician_required is True
        assert result.technician_reason is not None
        assert "swollen" in result.technician_reason.lower() or "battery" in result.technician_reason.lower()

    @pytest.mark.asyncio
    async def test_safety_escalation_tv_high_voltage(self, provider):
        request = DiagnosisRequest(
            device_category=DeviceCategory.TV,
            problem_description="TV power supply high voltage issue",
        )
        result, _ = await provider.diagnose(request)

        assert result.technician_required is True

    @pytest.mark.asyncio
    async def test_follow_up_questions_generated(self, provider, sample_request):
        result, _ = await provider.diagnose(sample_request)

        assert len(result.follow_up_questions) > 0
        for q in result.follow_up_questions:
            assert q.question is not None
            assert len(q.question) > 0

    @pytest.mark.asyncio
    async def test_safe_steps_are_safe(self, provider, sample_request):
        result, _ = await provider.diagnose(sample_request)

        for step in result.safe_steps:
            assert step.risk in (RiskLevel.SAFE, RiskLevel.LOW)
            assert step.instruction is not None
            assert step.purpose is not None

    @pytest.mark.asyncio
    async def test_health_check(self, provider):
        healthy = await provider.health_check()
        assert healthy is True


class TestMockAIProviderRiskLevels:
    @pytest.fixture
    def provider(self):
        return MockAIProvider()

    @pytest.mark.asyncio
    async def test_critical_severity_for_dangerous_keywords(self, provider):
        request = DiagnosisRequest(
            device_category=DeviceCategory.LAPTOP,
            problem_description="Smoke coming from laptop",
        )
        result, _ = await provider.diagnose(request)
        assert result.problem["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_high_severity_for_serious_keywords(self, provider):
        request = DiagnosisRequest(
            device_category=DeviceCategory.LAPTOP,
            problem_description="Laptop won't turn on black screen",
        )
        result, _ = await provider.diagnose(request)
        assert result.problem["severity"] in ("high", "critical")

    @pytest.mark.asyncio
    async def test_medium_severity_default(self, provider):
        request = DiagnosisRequest(
            device_category=DeviceCategory.LAPTOP,
            problem_description="Laptop running slowly",
        )
        result, _ = await provider.diagnose(request)
        assert result.problem["severity"] == "medium"