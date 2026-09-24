"""CORS: preflight и фактические ответы для пересортировки этапов.

Регрессия на ``Ensure CORS response header values are valid`` при перетаскивании
этапов: с ``allow_credentials=True`` FastAPI не должен отдавать ``*`` в
``Access-Control-Allow-Origin``, а preflight обязан вернуть 200 и полный набор
заголовков, иначе браузер блокирует PATCH/POST-запрос.
"""

from __future__ import annotations

import pytest
from app.core.config import get_settings
from app.db.session import create_tables
from app.main import app
from httpx import ASGITransport, AsyncClient

ALLOWED_ORIGIN = "http://localhost:5173"
# Хост стенда предпросмотра задаётся через CORS_ORIGIN_REGEX (см. conftest.py).
RUNTIME_ORIGIN = "https://feature-preview.preview.example.com"
FOREIGN_ORIGIN = "https://evil.example.com"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
async def _prepare_db():
    await create_tables()


@pytest.fixture(autouse=True)
def _restore_settings():
    yield
    get_settings.cache_clear()


async def test_preflight_reorder_returns_200_and_headers() -> None:
    async with _client() as client:
        response = await client.options(
            "/api/stages/reorder",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"
    allowed_methods = response.headers["access-control-allow-methods"].upper()
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
        assert method in allowed_methods
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    for header in ("authorization", "content-type", "accept", "x-requested-with"):
        assert header in allowed_headers


async def test_allow_origin_is_never_wildcard_with_credentials() -> None:
    async with _client() as client:
        response = await client.options(
            "/api/stages/reorder",
            headers={
                "Origin": ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
            },
        )
    assert response.headers["access-control-allow-origin"] != "*"


async def test_foreign_origin_is_rejected() -> None:
    async with _client() as client:
        response = await client.options(
            "/api/stages/reorder",
            headers={
                "Origin": FOREIGN_ORIGIN,
                "Access-Control-Request-Method": "POST",
            },
        )
    # Не наш origin: заголовка с разрешением быть не должно.
    assert "access-control-allow-origin" not in response.headers


async def test_preview_runtime_origin_is_allowed() -> None:
    async with _client() as client:
        response = await client.options(
            "/api/stages/reorder",
            headers={
                "Origin": RUNTIME_ORIGIN,
                "Access-Control-Request-Method": "POST",
            },
        )
    assert response.headers.get("access-control-allow-origin") == RUNTIME_ORIGIN


async def test_download_response_exposes_content_disposition(monkeypatch) -> None:
    """Фронт читает имя файла из Content-Disposition — заголовок должен быть виден."""
    from io import BytesIO

    from app.api import reports as reports_api
    from app.auth.security import get_current_user
    from app.models.entities import User
    from app.models.enums import UserRole

    async def _fake_user() -> User:
        return User(
            id=1,
            email="admin@rtk.ru",
            full_name="Админ",
            role=UserRole.ADMIN,
            is_active=True,
            hashed_password="x",
        )

    async def _fake_data(*args, **kwargs) -> list[dict]:
        return []

    app.dependency_overrides[get_current_user] = _fake_user
    monkeypatch.setattr(reports_api, "_build_interaction_data", _fake_data)
    monkeypatch.setattr(reports_api, "generate_xlsx", lambda data: BytesIO(b"xlsx"))
    try:
        async with _client() as client:
            response = await client.get("/api/reports/xlsx", headers={"Origin": ALLOWED_ORIGIN})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    exposed = response.headers["access-control-expose-headers"].lower()
    assert "content-disposition" in exposed
