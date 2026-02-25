import pytest
import os
import warnings

# Set environment variables BEFORE importing app modules
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["POSTGRES_DSN"] = "sqlite+aiosqlite:///file:wishshare_tests?mode=memory&cache=shared&uri=true"

warnings.filterwarnings("ignore", category=DeprecationWarning)

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app
from app.core.config import settings


def pytest_configure(config):
    warnings.filterwarnings("ignore", category=DeprecationWarning)

def pytest_sessionstart(session):
    warnings.simplefilter("ignore", DeprecationWarning)



@pytest.fixture(scope="session", autouse=True)
def disable_rate_limiting():
    """Disable rate limiting for all tests."""
    original = settings.rate_limit_enabled
    settings.rate_limit_enabled = False
    yield
    settings.rate_limit_enabled = original


@pytest.fixture
async def async_client(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
def test_client():
    """Synchronous test client with rate limiting disabled."""
    from fastapi.testclient import TestClient
    
    with TestClient(app) as client:
        yield client
