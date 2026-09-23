"""Журнал аудита действий (152-ФЗ).

Middleware пишет запись на каждую успешную мутацию, но без read-эндпоинта
данные журнала недоступны. Эти тесты фиксируют контракт чтения: доступ
только администратору, фильтры и сортировка от свежих к старым.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.auth.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.entities import ActionLog, University, User
from app.models.enums import UserRole


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        session.add_all(
            [
                User(
                    email="admin@a.ru",
                    full_name="Админ",
                    role=UserRole.ADMIN,
                    is_admin=True,
                    hashed_password=hash_password("pass"),
                ),
                User(
                    email="kam@a.ru",
                    full_name="КАМ",
                    role=UserRole.USER,
                    is_admin=False,
                    hashed_password=hash_password("pass"),
                ),
            ]
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _token(client: AsyncClient, email: str) -> dict[str, str]:
    r = await client.post(
        "/api/auth/login", json={"email": email, "password": "pass"}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _user_id(email: str) -> int:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        return user.id


async def _add_log(
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int = 1,
    created_at: datetime | None = None,
) -> None:
    async with SessionLocal() as session:
        session.add(
            ActionLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                created_at=created_at or datetime.utcnow(),
            )
        )
        await session.commit()


async def test_audit_requires_admin(client: AsyncClient) -> None:
    headers = await _token(client, "kam@a.ru")
    r = await client.get("/api/audit", headers=headers)
    assert r.status_code == 403


async def test_audit_requires_authentication(client: AsyncClient) -> None:
    r = await client.get("/api/audit")
    assert r.status_code == 401


async def test_audit_returns_entries_newest_first(client: AsyncClient) -> None:
    admin_id = await _user_id("admin@a.ru")
    older = datetime.utcnow() - timedelta(hours=1)
    await _add_log(admin_id, "CREATE", "Interaction", 1, older)
    await _add_log(admin_id, "UPDATE", "Interaction", 2, datetime.utcnow())

    headers = await _token(client, "admin@a.ru")
    r = await client.get("/api/audit", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    assert [item["action"] for item in body["items"]] == ["UPDATE", "CREATE"]
    assert body["items"][0]["user_name"] == "Админ"


async def test_audit_filters_by_action_and_entity(client: AsyncClient) -> None:
    admin_id = await _user_id("admin@a.ru")
    await _add_log(admin_id, "CREATE", "Interaction")
    await _add_log(admin_id, "DELETE", "University")
    await _add_log(admin_id, "UPDATE", "University")

    headers = await _token(client, "admin@a.ru")
    r = await client.get(
        "/api/audit", headers=headers, params={"entity_type": "University"}
    )
    assert r.json()["total"] == 2

    r = await client.get("/api/audit", headers=headers, params={"action": "delete"})
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["entity_type"] == "University"


async def test_audit_filters_by_user(client: AsyncClient) -> None:
    admin_id = await _user_id("admin@a.ru")
    kam_id = await _user_id("kam@a.ru")
    await _add_log(admin_id, "CREATE", "Interaction")
    await _add_log(kam_id, "UPDATE", "Interaction")

    headers = await _token(client, "admin@a.ru")
    r = await client.get("/api/audit", headers=headers, params={"user_id": kam_id})
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["user_name"] == "КАМ"


async def test_audit_pagination(client: AsyncClient) -> None:
    admin_id = await _user_id("admin@a.ru")
    base = datetime.utcnow()
    for i in range(5):
        await _add_log(admin_id, "CREATE", "Interaction", i, base + timedelta(seconds=i))

    headers = await _token(client, "admin@a.ru")
    r = await client.get(
        "/api/audit", headers=headers, params={"limit": 2, "offset": 1}
    )
    body = r.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2


async def test_audit_records_mutation_through_middleware(client: AsyncClient) -> None:
    """Реальная мутация через API должна попасть в журнал."""
    headers = await _token(client, "admin@a.ru")
    r = await client.post(
        "/api/universities", headers=headers, json={"name": "Аудит Вуз"}
    )
    assert r.status_code == 201, r.text

    r = await client.get(
        "/api/audit", headers=headers, params={"entity_type": "University"}
    )
    body = r.json()
    assert body["total"] >= 1
    assert body["items"][0]["action"] == "CREATE"
    assert body["items"][0]["user_name"] == "Админ"


async def test_entity_types_endpoint(client: AsyncClient) -> None:
    admin_id = await _user_id("admin@a.ru")
    await _add_log(admin_id, "CREATE", "Interaction")
    await _add_log(admin_id, "UPDATE", "University")

    headers = await _token(client, "admin@a.ru")
    r = await client.get("/api/audit/entity-types", headers=headers)
    assert r.status_code == 200
    assert set(r.json()) == {"Interaction", "University"}
