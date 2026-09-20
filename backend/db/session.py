from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from backend.core.config import get_settings
from backend.db.base import Base

engine = create_async_engine(
    get_settings().database_url,
    echo=False,
    pool_pre_ping=True,
    poolclass=NullPool,  # Важно для Supabase pooler (pgbouncer)
)

SessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncSession:
    """Зависимость FastAPI: сессия БД на время обработки запроса."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Создание таблиц. Используется в dev-режиме и в seed."""
    import backend.models  # noqa: F401  регистрирует модели в Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)


async def drop_all() -> None:
    """Удаление всех таблиц. Используется для миграций."""
    import backend.models  # noqa: F401  регистрирует модели в Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
