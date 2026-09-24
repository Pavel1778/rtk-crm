"""Тесты JSON-экспорта: ключи связи с БД, S3 и метаданные выгрузки."""

from __future__ import annotations

import pytest
from app.auth.security import create_access_token, hash_password
from app.db.session import SessionLocal, create_tables
from app.main import app
from app.models.entities import (
    AttachedFile,
    Interaction,
    ITDirection,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)
from app.models.enums import UserRole, WorkflowScope
from app.seed import seed_reference
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
async def _prepare_db():
    await create_tables()
    async with SessionLocal() as session:
        for model in (
            AttachedFile,
            Interaction,
            ITProduct,
            ITDirection,
            WorkflowStageRef,
            University,
            User,
        ):
            await session.execute(delete(model))
        await session.commit()
        await seed_reference(session)
    yield


async def _fixture_data() -> tuple[str, int]:
    """Создаёт вуз, продукт, взаимодействие и файл; возвращает токен и id."""
    async with SessionLocal() as session:
        user = User(
            email="admin-json@rtk.ru",
            full_name="Админ Экспорта",
            role=UserRole.ADMIN,
            is_admin=True,
            hashed_password=hash_password("secret123"),
        )
        session.add(user)

        university = University(name="ВУЗ им. Ленина №5")
        session.add(university)

        direction = ITDirection(name="Информационные технологии")
        session.add(direction)
        await session.flush()

        product = ITProduct(name="СЭД «Дело»", direction_id=direction.id)
        session.add(product)

        stage = await session.scalar(
            select(WorkflowStageRef)
            .where(WorkflowStageRef.scope == WorkflowScope.B2B)
            .order_by(WorkflowStageRef.order)
        )
        await session.commit()
        await session.refresh(user)
        await session.refresh(university)
        await session.refresh(product)

        interaction = Interaction(
            university_id=university.id,
            product_id=product.id,
            stage_id=stage.id,
            scope=WorkflowScope.B2B,
            assigned_kam_id=user.id,
            contract_number="№ 42/2026",
        )
        session.add(interaction)
        await session.flush()

        session.add(AttachedFile(
            interaction_id=interaction.id,
            filename="договор.pdf",
            file_path=f"interactions/{interaction.id}/abc.pdf",
            size=1024,
            mime_type="application/pdf",
            uploaded_by=user.id,
        ))
        await session.commit()

        return create_access_token(user), interaction.id


async def test_json_export_has_db_linkage_keys() -> None:
    token, interaction_id = await _fixture_data()
    async with _client() as client:
        response = await client.get(
            "/api/reports/json",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1

    item = body["interactions"][0]
    assert item["id"] == interaction_id
    # Ключи связи с БД: id сущностей и внешние ключи присутствуют и непусты.
    for key in ("university_id", "product_id", "stage_id", "direction_id", "assigned_kam_id"):
        assert item[key] is not None, f"нет ключа связи {key}"
    assert item["scope"] == "b2b"


async def test_json_export_has_s3_file_keys() -> None:
    token, interaction_id = await _fixture_data()
    async with _client() as client:
        response = await client.get(
            "/api/reports/json",
            headers={"Authorization": f"Bearer {token}"},
        )

    item = response.json()["interactions"][0]
    assert len(item["files"]) == 1

    attachment = item["files"][0]
    assert attachment["interaction_id"] == interaction_id
    assert attachment["filename"] == "договор.pdf"
    assert attachment["key"] == f"interactions/{interaction_id}/abc.pdf"
    # Локальный fallback: бакета нет, но ключ объекта сохранён.
    assert attachment["bucket"] is None
    assert "file_id" in attachment


async def test_json_export_includes_metadata_and_filters() -> None:
    token, _ = await _fixture_data()
    async with _client() as client:
        response = await client.get(
            "/api/reports/json?university_id=1&date_from=2026-01-01",
            headers={"Authorization": f"Bearer {token}"},
        )

    body = response.json()
    assert "generated_at" in body
    assert body["storage"]["type"] in {"local", "s3"}
    assert body["filters"]["university_id"] == 1
    assert body["filters"]["date_from"] == "2026-01-01"
    assert body["filters"]["stage_id"] is None
