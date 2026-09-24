"""Тесты системных эндпоинтов: healthz/readyz и лимит попыток входа."""

from __future__ import annotations

import pytest
from app.core.config import get_settings
from app.db.session import create_tables
from app.main import app
from app.middleware.rate_limit import _login_attempts
from httpx import ASGITransport, AsyncClient


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
async def _prepare_db():
    await create_tables()


async def test_healthz_is_liveness_only() -> None:
    async with _client() as client:
        response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readyz_reports_dependency_checks() -> None:
    async with _client() as client:
        response = await client.get("/readyz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    # Без REDIS_URL и S3_ENDPOINT зависимости считаются отключёнными,
    # а не недоступными — это не делает сервис not ready.
    assert body["checks"]["cache"] == "disabled"
    assert body["checks"]["storage"] == "local"


async def test_login_is_rate_limited_after_failed_attempts() -> None:
    _login_attempts.clear()
    settings = get_settings()
    limit = settings.login_rate_limit
    assert limit > 0, "для теста лимит должен быть включён"

    async with _client() as client:
        payload = {"email": "nobody@rtk.ru", "password": "wrong-password"}
        statuses = []
        for _ in range(limit + 1):
            response = await client.post("/api/auth/login", json=payload)
            statuses.append(response.status_code)

    assert statuses[:limit] == [401] * limit
    assert statuses[limit] == 429
    # Счётчик должен остаться очищаемым между тестами.
    _login_attempts.clear()
