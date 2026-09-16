from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Supabase даёт URL с postgresql://, но для asyncpg нужен postgresql+asyncpg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Убираем несовместимые параметры из URL (asyncpg не поддерживает sslmode через URL)
if "?sslmode=" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?")[0]

# Fallback для локальной разработки
if not DATABASE_URL:
    DATABASE_URL = "postgresql+asyncpg://rtk_user:rtk_password@localhost:5432/rtk_crm"

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "False") == "True",
    pool_size=5,  # Уменьшено для free tier Render
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"ssl": "require"} if "supabase" in DATABASE_URL else {},
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
