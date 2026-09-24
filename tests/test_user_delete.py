"""Удаление сотрудника администратором.

Пользователь может быть связан с историей: он автор действий/комментариев,
загружал файлы, назначен КАМом на взаимодействия, присутствует в журнале
аудита. FK на `users.id` объявлены с `ondelete="SET NULL"`, поэтому удаление
учётной записи должно обнулять ссылки, а не падать с нарушением ограничения.
"""

from __future__ import annotations

import pytest_asyncio
from app.auth.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.entities import (
    Action,
    ActionLog,
    AttachedFile,
    Comment,
    Interaction,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)
from app.models.enums import UserRole, WorkflowScope
from httpx import ASGITransport, AsyncClient


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
        session.add_all([admin, kam])
        await session.commit()

        uni = University(name="Вуз А")
        product = ITProduct(name="Продукт А")
        stage = WorkflowStageRef(
            code="contact_search",
            name="Этап 1",
            order=1,
            scope=WorkflowScope.B2B,
            is_active=True,
        )
        session.add_all([uni, product, stage])
        await session.commit()

        interaction = Interaction(
            university_id=uni.id,
            product_id=product.id,
            stage_id=stage.id,
            scope=WorkflowScope.B2B,
            assigned_kam_id=kam.id,
            is_active=True,
        )
        session.add(interaction)
        await session.commit()

        session.add_all(
            [
                Action(interaction_id=interaction.id, title="Задача", author_id=kam.id),
                Comment(interaction_id=interaction.id, text="Комментарий", author_id=kam.id),
                AttachedFile(
                    interaction_id=interaction.id,
                    filename="c.pdf",
                    file_path="uploads/c.pdf",
                    size=10,
                    mime_type="application/pdf",
                    uploaded_by=kam.id,
                ),
                ActionLog(
                    user_id=kam.id,
                    action="CREATE",
                    entity_type="Interaction",
                    entity_id=interaction.id,
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
    r = await client.post("/api/auth/login", json={"email": email, "password": "pass"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _id(email: str) -> int:
    async with SessionLocal() as session:
        from sqlalchemy import select

        user = await session.scalar(select(User).where(User.email == email))
        assert user is not None
        return user.id


async def test_delete_user_with_history(client: AsyncClient) -> None:
    """Удаление сотрудника с историей не должно падать."""
    headers = await _token(client, "admin@t.ru")
    kam_id = await _id("kam@t.ru")

    r = await client.delete(f"/api/auth/users/{kam_id}", headers=headers)
    assert r.status_code == 204, f"Ожидался 204, получено {r.status_code}: {r.text}"

    async with SessionLocal() as session:
        assert await session.get(User, kam_id) is None


async def test_delete_self_forbidden(client: AsyncClient) -> None:
    headers = await _token(client, "admin@t.ru")
    admin_id = await _id("admin@t.ru")
    r = await client.delete(f"/api/auth/users/{admin_id}", headers=headers)
    assert r.status_code == 400
