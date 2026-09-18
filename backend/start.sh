#!/bin/bash
# Старт backend на Render: схема + справочники + uvicorn.
set -e

echo "==> Инициализация схемы БД и справочников"
python - <<'PY'
import asyncio

from backend.db.session import SessionLocal, create_tables
from backend.seed import seed_reference

async def init() -> None:
    await create_tables()
    async with SessionLocal() as session:
        await seed_reference(session)

asyncio.run(init())
PY

echo "==> Запуск uvicorn на порту ${PORT:-8000}"
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}"
