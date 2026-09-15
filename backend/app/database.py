from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://rtk_user:rtk_password@localhost:5432/rtk_crm"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "False") == "True",
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=0,
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
