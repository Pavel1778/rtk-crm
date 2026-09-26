from collections.abc import AsyncGenerator

from app.core.config import get_settings
from app.db.base import Base
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

engine = create_async_engine(
    get_settings().database_url,
    echo=False,
    pool_pre_ping=True,
    # NullPool: соединение закрывается сразу после использования.
    # Нужен при работе через внешний пулер (pgbouncer Yandex Managed
    # PostgreSQL в режиме transaction pooling) — иначе соединения
    # «залипают» в процессе и не отдаются обратно в пулер.
    poolclass=NullPool,
)

SessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость FastAPI: сессия БД на время обработки запроса."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Создание таблиц. Используется в dev-режиме и в seed."""
    import app.models  # noqa: F401  регистрирует модели в Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)


async def drop_all() -> None:
    """Удаление всех таблиц. Используется для миграций."""
    import app.models  # noqa: F401  регистрирует модели в Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
