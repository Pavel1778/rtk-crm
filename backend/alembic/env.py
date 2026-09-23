"""Окружение Alembic для async SQLAlchemy.

URL берётся из настроек приложения (DATABASE_URL), поэтому миграции всегда
идут в ту же БД, что и сервис. Для offline-режима достаточно sync-URL.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Пакет `app` в репозитории лежит в каталоге backend/ (в контейнере он
# копируется в /app). Для локального запуска alembic создаём alias app->backend,
# так же как это делает conftest.py для тестов.
BACKEND_DIR = Path(__file__).resolve().parents[1]
_alias_dir = Path(tempfile.mkdtemp(prefix="rtk-alembic-alias-"))
_alias_path = _alias_dir / "app"
if not _alias_path.exists():
    _alias_path.symlink_to(BACKEND_DIR, target_is_directory=True)
if str(_alias_dir) not in sys.path:
    sys.path.insert(0, str(_alias_dir))

from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401  регистрирует модели в Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Генерация SQL без подключения к БД (alembic upgrade --sql)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
