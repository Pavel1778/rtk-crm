"""Права доступа к взаимодействиям и назначение ответственного КАМ.

ТЗ (раздел про роли): КАМ (`user`) работает только со своими взаимодействиями,
руководитель (`manager`) и администратор видят все. Разграничение должно
действовать не только на списке и доске, но и на операциях по id — иначе
зная чужой id, КАМ может прочитать, изменить или удалить чужую карточку.
"""

from __future__ import annotations

import pytest_asyncio
from app.auth.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.entities import (
    Interaction,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)
from app.models.enums import UserRole, WorkflowScope
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        admin = User(
            email="admin@t.ru",
            full_name="Админ",
            role=UserRole.ADMIN,
            is_admin=True,
            hashed_password=hash_password("pass"),
        )
        kam = User(
            email="kam@t.ru",
            full_name="КАМ Один",
            role=UserRole.USER,
            is_admin=False,
            hashed_password=hash_password("pass"),
        )
        kam2 = User(
            email="kam2@t.ru",
            full_name="КАМ Два",
            role=UserRole.USER,
            is_admin=False,
            hashed_password=hash_password("pass"),
        )
        manager = User(
            email="mgr@t.ru",
            full_name="Руководитель",
            role=UserRole.MANAGER,
            is_admin=False,
            hashed_password=hash_password("pass"),
        )
        session.add_all([admin, kam, kam2, manager])
        session.add(University(name="Вуз А"))
        session.add(University(name="Вуз Б"))
        session.add(ITProduct(name="Продукт А"))
        session.add(
            WorkflowStageRef(
                code="contact_search",
                name="Этап 1",
                order=1,
                scope=WorkflowScope.B2B,
                is_active=True,
            )
        )
        session.add(
            WorkflowStageRef(
                code="meeting",
                name="Этап 2",
                order=2,
                scope=WorkflowScope.B2B,
                is_active=True,
            )
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


async def _names() -> dict[str, int]:
    async with SessionLocal() as session:
        rows = (await session.scalars(select(User))).all()
        return {u.email: u.id for u in rows}


async def _seed_foreign_interaction(owner_email: str) -> int:
    """Создаёт взаимодействие, назначенное указанному КАМ."""
    ids = await _names()
    async with SessionLocal() as session:
        uni = await session.scalar(select(University).where(University.name == "Вуз А"))
        stage = await session.scalar(
            select(WorkflowStageRef).where(WorkflowStageRef.order == 1)
        )
        interaction = Interaction(
            university_id=uni.id,
            stage_id=stage.id,
            scope=WorkflowScope.B2B,
            assigned_kam_id=ids[owner_email],
            is_active=True,
        )
        session.add(interaction)
        await session.commit()
        return interaction.id


async def test_kam_cannot_read_foreign_interaction(client: AsyncClient) -> None:
    headers = await _token(client, "kam@t.ru")
    foreign_id = await _seed_foreign_interaction("kam2@t.ru")
    r = await client.get(f"/api/interactions/{foreign_id}", headers=headers)
    assert r.status_code in (403, 404), (
        f"КАМ не должен читать чужую карточку, получено {r.status_code}"
    )


async def test_kam_cannot_update_foreign_interaction(client: AsyncClient) -> None:
    headers = await _token(client, "kam@t.ru")
    foreign_id = await _seed_foreign_interaction("kam2@t.ru")
    r = await client.patch(
        f"/api/interactions/{foreign_id}", headers=headers, json={"notes": "x"}
    )
    assert r.status_code in (403, 404)


async def test_kam_cannot_move_foreign_interaction(client: AsyncClient) -> None:
    headers = await _token(client, "kam@t.ru")
    foreign_id = await _seed_foreign_interaction("kam2@t.ru")
    async with SessionLocal() as session:
        stage2 = await session.scalar(
            select(WorkflowStageRef).where(WorkflowStageRef.order == 2)
        )
    r = await client.post(
        f"/api/interactions/{foreign_id}/move",
        headers=headers,
        params={"stage_id": stage2.id},
    )
    assert r.status_code in (403, 404)


async def test_kam_cannot_delete_foreign_interaction(client: AsyncClient) -> None:
    headers = await _token(client, "kam@t.ru")
    foreign_id = await _seed_foreign_interaction("kam2@t.ru")
    r = await client.delete(f"/api/interactions/{foreign_id}", headers=headers)
    assert r.status_code in (403, 404)

    async with SessionLocal() as session:
        still = await session.get(Interaction, foreign_id)
    assert still is not None, "чужая карточка не должна быть удалена"


async def test_kam_cannot_comment_foreign_interaction(client: AsyncClient) -> None:
    headers = await _token(client, "kam@t.ru")
    foreign_id = await _seed_foreign_interaction("kam2@t.ru")
    r = await client.post(
        f"/api/interactions/{foreign_id}/comments",
        headers=headers,
        json={"text": "чужой комментарий"},
    )
    assert r.status_code in (403, 404)


async def test_manager_can_read_any_interaction(client: AsyncClient) -> None:
    headers = await _token(client, "mgr@t.ru")
    foreign_id = await _seed_foreign_interaction("kam2@t.ru")
    r = await client.get(f"/api/interactions/{foreign_id}", headers=headers)
    assert r.status_code == 200


async def test_kam_can_access_own_interaction(client: AsyncClient) -> None:
    headers = await _token(client, "kam@t.ru")
    own_id = await _seed_foreign_interaction("kam@t.ru")
    r = await client.get(f"/api/interactions/{own_id}", headers=headers)
    assert r.status_code == 200


async def test_create_interaction_assigns_kam(client: AsyncClient) -> None:
    """Поле assigned_kam_id из запроса должно сохраняться при создании."""
    headers = await _token(client, "admin@t.ru")
    ids = await _names()
    async with SessionLocal() as session:
        uni = await session.scalar(select(University).where(University.name == "Вуз Б"))
        product = await session.scalar(select(ITProduct))
        stage = await session.scalar(
            select(WorkflowStageRef).where(WorkflowStageRef.order == 1)
        )

    r = await client.post(
        "/api/interactions",
        headers=headers,
        json={
            "university_id": uni.id,
            "product_id": product.id,
            "stage_id": stage.id,
            "assigned_kam_id": ids["kam2@t.ru"],
            "scope": "b2b",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["assigned_kam_id"] == ids["kam2@t.ru"]


async def test_kam_create_assigns_self(client: AsyncClient) -> None:
    """КАМ создаёт карточку — ответственным становится он сам."""
    headers = await _token(client, "kam@t.ru")
    ids = await _names()
    async with SessionLocal() as session:
        uni = await session.scalar(select(University).where(University.name == "Вуз Б"))
        product = await session.scalar(select(ITProduct))

    r = await client.post(
        "/api/interactions",
        headers=headers,
        json={
            "university_id": uni.id,
            "product_id": product.id,
            "scope": "b2b",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["assigned_kam_id"] == ids["kam@t.ru"]


async def test_kam_cannot_upload_to_foreign_interaction(client: AsyncClient) -> None:
    """Файлы наследуют доступ взаимодействия — загрузка к чужой карточке запрещена."""
    foreign_id = await _seed_foreign_interaction("kam2@t.ru")
    headers = await _token(client, "kam@t.ru")
    r = await client.post(
        f"/api/files/interactions/{foreign_id}/upload",
        headers=headers,
        files={"file": ("note.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert r.status_code == 403, r.text


async def test_kam_cannot_list_foreign_files(client: AsyncClient) -> None:
    foreign_id = await _seed_foreign_interaction("kam2@t.ru")
    headers = await _token(client, "kam@t.ru")
    r = await client.get(
        f"/api/files/interactions/{foreign_id}", headers=headers
    )
    assert r.status_code == 403, r.text


async def test_kam_can_upload_own_and_download_own(client: AsyncClient) -> None:
    own_id = await _seed_foreign_interaction("kam@t.ru")
    headers = await _token(client, "kam@t.ru")
    r = await client.post(
        f"/api/files/interactions/{own_id}/upload",
        headers=headers,
        files={"file": ("note.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert r.status_code == 201, r.text
    file_id = r.json()["id"]

    r = await client.get(f"/api/files/{file_id}/download", headers=headers)
    assert r.status_code == 200, r.text
    assert r.content == b"%PDF-1.4 test"


async def test_kam_cannot_download_foreign_file(client: AsyncClient) -> None:
    foreign_id = await _seed_foreign_interaction("kam2@t.ru")
    owner_headers = await _token(client, "kam2@t.ru")
    r = await client.post(
        f"/api/files/interactions/{foreign_id}/upload",
        headers=owner_headers,
        files={"file": ("note.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert r.status_code == 201, r.text
    file_id = r.json()["id"]

    headers = await _token(client, "kam@t.ru")
    r = await client.get(f"/api/files/{file_id}/download", headers=headers)
    assert r.status_code == 403, r.text


async def test_manager_can_download_any_file(client: AsyncClient) -> None:
    foreign_id = await _seed_foreign_interaction("kam2@t.ru")
    owner_headers = await _token(client, "kam2@t.ru")
    r = await client.post(
        f"/api/files/interactions/{foreign_id}/upload",
        headers=owner_headers,
        files={"file": ("note.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    file_id = r.json()["id"]

    headers = await _token(client, "mgr@t.ru")
    r = await client.get(f"/api/files/{file_id}/download", headers=headers)
    assert r.status_code == 200, r.text

