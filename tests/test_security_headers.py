"""Тесты заголовков безопасности ответа."""

from __future__ import annotations

from app.core.config import get_settings
from app.main import app
from httpx import ASGITransport, AsyncClient


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_security_headers_present_on_api() -> None:
    async with _client() as client:
        response = await client.get("/healthz")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


async def test_docs_are_exempt_from_csp() -> None:
    # Swagger UI использует инлайновые скрипты — CSP их сломает.
    async with _client() as client:
        response = await client.get("/docs")

    assert response.status_code == 200
    assert "content-security-policy" not in response.headers
    assert response.headers["x-frame-options"] == "DENY"


async def test_hsts_only_in_production(monkeypatch) -> None:
    settings = get_settings()

    monkeypatch.setattr(settings, "environment", "production")
    async with _client() as client:
        response = await client.get("/healthz")
    assert "strict-transport-security" in response.headers

    monkeypatch.setattr(settings, "environment", "development")
    async with _client() as client:
        response = await client.get("/healthz")
    assert "strict-transport-security" not in response.headers


async def test_headers_present_on_error_response() -> None:
    # 401 формируется внутри приложения — внешний слой всё равно должен
    # добавить заголовки.
    async with _client() as client:
        response = await client.get("/api/interactions")

    assert response.status_code == 401
    assert response.headers["x-content-type-options"] == "nosniff"
