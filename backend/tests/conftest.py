import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.db.database import Base, get_db
from app.main import app
from app.core.config import Settings


@pytest.fixture(scope="session")
def test_settings():
    return Settings(
        APP_ENV="testing",
        DATABASE_URL="postgresql+asyncpg://fixcare:fixcare_test@localhost:5432/fixcare_test",
        AI_PROVIDER="mock",
        JWT_SECRET="test-secret-key-for-testing-only",
        CORS_ORIGINS=["http://localhost:3000"],
    )


@pytest_asyncio.fixture(scope="function")
async def db_engine(test_settings):
    engine = create_async_engine(
        test_settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()