"""Сводка по взаимодействию через GigaChat (ФТ-6).

Внешний сервис не вызывается: httpx подменяется транспортом, который
отвечает как GigaChat. Проверяется реальный путь — сборка промпта, два шага
авторизации (Basic на OAuth, Bearer к модели), разбор ответа, кэш токена и
коды ошибок. Мок здесь уместен, потому что GigaChat — платный внешний
сервис, недоступный в CI, а не часть нашего кода.
"""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from app.auth.security import hash_password
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.entities import (
    Action,
    Comment,
    Interaction,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)
from app.models.enums import UserRole, WorkflowScope
from app.services import gigachat
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

ACCESS_TOKEN = "test-access-token"
SUMMARY_TEXT = "Вуз на этапе переговоров. Готовится коммерческое предложение."


class FakeGigaChat:
    """Транспорт, отвечающий как GigaChat, и счётчики обращений."""

    def __init__(self) -> None:
        self.oauth_calls = 0
        self.chat_calls = 0
        self.last_chat_body: dict = {}
        self.oauth_headers: dict = {}
        self.fail_oauth = False
        self.fail_chat = False
        self.chat_status = 200
        self.chat_payload: dict = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/api/v2/oauth"):
            self.oauth_calls += 1
            self.oauth_headers = dict(request.headers)
            if self.fail_oauth:
                return httpx.Response(401, json={"error": "invalid_client"})
            return httpx.Response(
                200,
                json={"access_token": ACCESS_TOKEN, "expires_at": 9999999999999},
            )
        if url.endswith("/chat/completions"):
            self.chat_calls += 1
            import json

            self.last_chat_body = json.loads(request.content)
            if self.fail_chat:
                return httpx.Response(500, json={"error": "internal"})
            if self.chat_status != 200:
                return httpx.Response(self.chat_status, json={"error": "bad"})
            payload = self.chat_payload or {
                "choices": [{"message": {"content": SUMMARY_TEXT}}]
            }
            return httpx.Response(200, json=payload)
        raise AssertionError(f"Неожиданный запрос к GigaChat: {url}")


@pytest.fixture
def fake_http(monkeypatch: pytest.MonkeyPatch) -> FakeGigaChat:
    """Подменяет httpx.post транспортом-заглушкой GigaChat."""
    import json

    fake = FakeGigaChat()
    transport = httpx.MockTransport(fake)

    def fake_post(url: str, **kwargs):
        content = kwargs.get("content")
        if "json" in kwargs:
            content = json.dumps(kwargs["json"]).encode()
        request = httpx.Request(
            "POST",
            url,
            headers=kwargs.get("headers"),
            content=content,
            data=kwargs.get("data"),
        )
        response = transport.handle_request(request)
        # MockTransport не привязывает request к ответу, а без него падает
        # raise_for_status — так же ведёт себя реальный httpx.Client.
        response.request = request
        return response

    monkeypatch.setattr(gigachat.httpx, "post", fake_post)
    return fake


@pytest.fixture(autouse=True)
def _gigachat_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GIGACHAT_CREDENTIALS", "test-basic-key")
    monkeypatch.setenv("GIGACHAT_MODEL", "GigaChat")
    get_settings.cache_clear()
    gigachat.reset_token_cache()
    yield
    get_settings.cache_clear()
    gigachat.reset_token_cache()


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        kam = User(
            email="kam@t.ru",
            full_name="КАМ Один",
            role=UserRole.USER,
            hashed_password=hash_password("pass"),
        )
        other = User(
            email="other@t.ru",
            full_name="КАМ Другой",
            role=UserRole.USER,
            hashed_password=hash_password("pass"),
        )
        admin = User(
            email="admin@t.ru",
            full_name="Админ",
            role=UserRole.ADMIN,
            is_admin=True,
            hashed_password=hash_password("pass"),
        )
        session.add_all([kam, other, admin])
        await session.flush()

        university = University(name="Тестовый Вуз", city="Москва")
        session.add(university)
        await session.flush()

        product = ITProduct(name="Платформа")
        session.add(product)
        stage = WorkflowStageRef(
            code="neg", name="Переговоры", order=1, scope=WorkflowScope.B2B
        )
        session.add_all([product, stage])
        await session.flush()

        own = Interaction(
            university_id=university.id,
            product_id=product.id,
            stage_id=stage.id,
            scope=WorkflowScope.B2B,
            assigned_kam_id=kam.id,
        )
        foreign = Interaction(
            university_id=university.id,
            product_id=product.id,
            stage_id=stage.id,
            scope=WorkflowScope.B2B,
            assigned_kam_id=other.id,
        )
        session.add_all([own, foreign])
        await session.flush()

        session.add_all(
            [
                Action(
                    interaction_id=own.id,
                    title="Отправить КП",
                    is_completed=False,
                    due_date="2026-10-01",
                ),
                Comment(interaction_id=own.id, text="Созвон прошёл успешно"),
            ]
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/auth/login", json={"email": email, "password": "pass"}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def _own_interaction_id(client: AsyncClient, token: str) -> int:
    response = await client.get(
        "/api/interactions", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    return response.json()[0]["id"]


async def test_summary_returns_text(
    client: AsyncClient, fake_http: FakeGigaChat
) -> None:
    token = await _login(client, "kam@t.ru")
    interaction_id = await _own_interaction_id(client, token)

    response = await client.post(
        f"/api/interactions/{interaction_id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == SUMMARY_TEXT
    assert body["model"] == "GigaChat"
    assert body["interaction_id"] == interaction_id


async def test_prompt_contains_card_data(
    client: AsyncClient, fake_http: FakeGigaChat
) -> None:
    """В промпт попадают вуз, этап, задачи и комментарии."""
    token = await _login(client, "kam@t.ru")
    interaction_id = await _own_interaction_id(client, token)

    await client.post(
        f"/api/interactions/{interaction_id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )

    user_message = fake_http.last_chat_body["messages"][1]["content"]
    assert "Тестовый Вуз" in user_message
    assert "Переговоры" in user_message
    assert "Отправить КП" in user_message
    assert "Созвон прошёл успешно" in user_message
    # Системная инструкция задаёт роль и запрет на выдумывание фактов.
    system_message = fake_http.last_chat_body["messages"][0]["content"]
    assert "Не выдумывай факты" in system_message


async def test_authorization_uses_basic_then_bearer(
    client: AsyncClient, fake_http: FakeGigaChat
) -> None:
    """OAuth вызывается с Basic-ключом, модель — с Bearer-токеном."""
    token = await _login(client, "kam@t.ru")
    interaction_id = await _own_interaction_id(client, token)

    await client.post(
        f"/api/interactions/{interaction_id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert fake_http.oauth_calls == 1
    assert fake_http.oauth_headers["authorization"] == "Basic test-basic-key"
    # RqUID обязателен для OAuth GigaChat.
    assert fake_http.oauth_headers.get("rquid")


async def test_token_is_cached_between_requests(
    client: AsyncClient, fake_http: FakeGigaChat
) -> None:
    """Повторные сводки не запрашивают токен заново."""
    token = await _login(client, "kam@t.ru")
    interaction_id = await _own_interaction_id(client, token)

    for _ in range(3):
        response = await client.post(
            f"/api/interactions/{interaction_id}/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    assert fake_http.oauth_calls == 1
    assert fake_http.chat_calls == 3


async def test_disabled_without_credentials(
    client: AsyncClient,
    fake_http: FakeGigaChat,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Без ключа функция выключена: 503, а не 500."""
    monkeypatch.setenv("GIGACHAT_CREDENTIALS", "")
    get_settings.cache_clear()
    gigachat.reset_token_cache()

    token = await _login(client, "kam@t.ru")
    interaction_id = await _own_interaction_id(client, token)

    response = await client.post(
        f"/api/interactions/{interaction_id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 503
    assert fake_http.chat_calls == 0


async def test_upstream_failure_returns_502(
    client: AsyncClient, fake_http: FakeGigaChat
) -> None:
    fake_http.fail_chat = True
    token = await _login(client, "kam@t.ru")
    interaction_id = await _own_interaction_id(client, token)

    response = await client.post(
        f"/api/interactions/{interaction_id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 502


async def test_oauth_failure_returns_502(
    client: AsyncClient, fake_http: FakeGigaChat
) -> None:
    fake_http.fail_oauth = True
    token = await _login(client, "kam@t.ru")
    interaction_id = await _own_interaction_id(client, token)

    response = await client.post(
        f"/api/interactions/{interaction_id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 502


async def test_unexpected_payload_returns_502(
    client: AsyncClient, fake_http: FakeGigaChat
) -> None:
    fake_http.chat_payload = {"unexpected": True}
    token = await _login(client, "kam@t.ru")
    interaction_id = await _own_interaction_id(client, token)

    response = await client.post(
        f"/api/interactions/{interaction_id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 502


async def test_summary_of_foreign_interaction_denied(
    client: AsyncClient, fake_http: FakeGigaChat
) -> None:
    """КАМ не получает сводку по чужому взаимодействию."""
    token = await _login(client, "kam@t.ru")

    async with SessionLocal() as session:
        other = await session.scalar(select(User).where(User.email == "other@t.ru"))
        foreign = await session.scalar(
            select(Interaction).where(Interaction.assigned_kam_id == other.id)
        )
        foreign_id = foreign.id

    response = await client.post(
        f"/api/interactions/{foreign_id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    # 403, а не 404: карточка существует, но недоступна этому КАМ.
    assert response.status_code == 403
    # Данные чужой карточки не ушли во внешний сервис.
    assert fake_http.chat_calls == 0


async def test_summary_requires_authentication(
    client: AsyncClient, fake_http: FakeGigaChat
) -> None:
    response = await client.post("/api/interactions/1/summary")
    assert response.status_code == 401
    assert fake_http.chat_calls == 0


async def test_build_prompt_handles_empty_card() -> None:
    """Карточка без задач и комментариев не ломает сборку промпта."""
    prompt = gigachat.build_prompt({"university_name": "Вуз"})
    assert "Вуз" in prompt
    assert "не назначен" in prompt


async def test_summarize_raises_disabled_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIGACHAT_CREDENTIALS", "")
    get_settings.cache_clear()
    gigachat.reset_token_cache()
    with pytest.raises(gigachat.GigaChatDisabled):
        gigachat.summarize({"university_name": "Вуз"})
