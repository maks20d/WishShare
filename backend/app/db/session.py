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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
