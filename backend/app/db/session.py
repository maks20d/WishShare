import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


engine = create_async_engine(
    settings.postgres_dsn,
    echo=False,
    future=True,
    # Validate connections before use — prevents "connection closed" errors
    # after long idle periods (especially important for PostgreSQL on Render/Supabase).
    pool_pre_ping=True,
)


class Base(DeclarativeBase):
    pass


async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)

_schema_ready = False
_schema_lock = asyncio.Lock()


async def ensure_schema_ready() -> None:
    """Create DB tables once for environments where startup hooks are skipped."""
    global _schema_ready
    if _schema_ready:
        return

    async with _schema_lock:
        if _schema_ready:
            return

        # Ensure models are imported so metadata contains all tables.
        from app.models import models as _models  # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        _schema_ready = True


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    await ensure_schema_ready()
    async with async_session_factory() as session:
        yield session
