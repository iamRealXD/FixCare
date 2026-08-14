import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from app.main import app
from app.db.models.user import User
from app.db.models.diagnosis import Diagnosis, DiagnosisStatus
from app.core.security import create_access_token


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