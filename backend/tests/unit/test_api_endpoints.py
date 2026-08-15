import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from app.main import app
from app.db.models.user import User
from app.db.models.diagnosis import Diagnosis, DiagnosisMessage, DiagnosisResult, DiagnosisStatus
from app.core.security import create_access_token
from app.schemas.diagnosis import DiagnosisRequest, DeviceCategory
from app.services.ai.factory import AIProviderFactory
from app.services.ai.mock_provider import MockAIProvider
from app.services.diagnosis_service import DiagnosisService
from sqlalchemy import select


@pytest.fixture
def test_user():
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        full_name="Test User",
        is_active=True,
    )


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_health_check(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ("ok", "degraded")
            assert "version" in data
            assert "environment" in data

    @pytest.mark.asyncio
    async def test_readiness_check(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
            assert response.status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_liveness_check(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health/live")
            assert response.status_code == 200
            assert response.json()["status"] == "alive"


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_register_validation_error(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "invalid", "password": "short"},
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "nonexistent@example.com", "password": "password123"},
            )
            assert response.status_code == 401


class TestDiagnosisEndpoints:
    @pytest.mark.asyncio
    async def test_create_diagnosis_unauthorized(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/diagnosis",
                json={
                    "device_category": "laptop",
                    "problem_description": "Laptop won't turn on",
                },
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_diagnosis_validation_error(self, auth_headers):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/diagnosis",
                headers=auth_headers,
                json={
                    "device_category": "invalid",
                    "problem_description": "Short",
                },
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_diagnoses_unauthorized(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/diagnosis")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_follow_up_answers_rerun_existing_diagnosis(
        self,
        client,
        db_session,
        test_user,
        auth_headers,
        monkeypatch,
    ):
        class CapturingMockProvider(MockAIProvider):
            requests: list[DiagnosisRequest] = []

            async def diagnose(self, request, diagnosis_id=None):
                self.requests.append(request)
                return await super().diagnose(request, diagnosis_id)

        provider = CapturingMockProvider()
        monkeypatch.setattr(
            AIProviderFactory,
            "get_provider",
            staticmethod(lambda: provider),
        )

        db_session.add(test_user)
        await db_session.commit()

        service = DiagnosisService(db_session)
        diagnosis = await service.create_diagnosis(
            test_user.id,
            DiagnosisRequest(
                device_category=DeviceCategory.LAPTOP,
                problem_description=(
                    "My laptop powers on but the display remains black after startup."
                ),
                brand="Framework",
                model="Laptop 13",
            ),
        )
        await service.run_diagnosis(diagnosis.id)

        response = await client.post(
            f"/api/v1/diagnosis/{diagnosis.id}/follow-up",
            headers=auth_headers,
            json={
                "answers": [
                    {
                        "question": "Does an external display work?",
                        "answer": "Yes, an external display works normally.",
                    }
                ]
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == str(diagnosis.id)
        assert payload["result"]["device"] == {
            "category": "laptop",
            "brand": "Framework",
            "model": "Laptop 13",
        }
        assert payload["result"]["problem"]["summary"] == (
            "My laptop powers on but the display remains black after startup."
        )
        assert len(provider.requests) == 2
        assert [
            answer.model_dump()
            for answer in provider.requests[-1].follow_up_answers
        ] == [
            {
            "question": "Does an external display work?",
            "answer": "Yes, an external display works normally.",
        }
        ]

        result_rows = await db_session.execute(
            select(DiagnosisResult).where(DiagnosisResult.diagnosis_id == diagnosis.id)
        )
        assert len(result_rows.scalars().all()) == 1

        message_rows = await db_session.execute(
            select(DiagnosisMessage)
            .where(DiagnosisMessage.diagnosis_id == diagnosis.id)
            .order_by(DiagnosisMessage.sequence)
        )
        assert [message.sequence for message in message_rows.scalars().all()] == [0, 1]


class TestDeviceEndpoints:
    @pytest.mark.asyncio
    async def test_create_device_unauthorized(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/devices",
                json={
                    "name": "Test Device",
                    "category": "laptop",
                },
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_devices_unauthorized(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/devices")
            assert response.status_code == 401


class TestUserEndpoints:
    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/users/me")
            assert response.status_code == 401
