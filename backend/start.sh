#!/bin/bash
# Старт backend на Render без Docker: схема + справочники + uvicorn.
#
# Приложение импортируется как пакет `app`, тогда как в репозитории исходники
# лежат в `backend/`. Поэтому создаём временный каталог с ссылкой `app ->
# backend` и добавляем его в PYTHONPATH — тот же приём, что в conftest.py и
# scripts/_bootstrap.py.
set -e

BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_ALIAS_DIR="$(mktemp -d)"
ln -sfn "$BACKEND_DIR" "$APP_ALIAS_DIR/app"
export PYTHONPATH="${APP_ALIAS_DIR}${PYTHONPATH:+:$PYTHONPATH}"

echo "==> Инициализация схемы БД и справочников"
python - <<'PY'
import asyncio

from app.db.schema_sync import ensure_schema
from app.db.session import SessionLocal, create_tables
from app.seed import seed_reference

async def init() -> None:
    await create_tables()
    # Доводим схему, созданную ранней версией приложения: create_all
    # существующие таблицы не меняет, из-за чего падал seed на проде.
    await ensure_schema()
    async with SessionLocal() as session:
        await seed_reference(session)

asyncio.run(init())
PY

echo "==> Запуск uvicorn на порту ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
