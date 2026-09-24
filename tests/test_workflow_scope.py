"""Тесты B2B/B2C workflow и лимита параллельных взаимодействий."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

import pytest
from app.auth.security import create_access_token, hash_password
from app.db.session import SessionLocal, create_tables
from app.main import app
from app.models.entities import (
    Interaction,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)
from app.models.enums import B2C_STAGES, UserRole, WorkflowScope
from app.seed import WORKFLOW_STAGES, seed_reference
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
async def _prepare_db():
    """Чистая БД на SQLite с заполненными справочниками для каждого теста."""
    await create_tables()
    async with SessionLocal() as session:
        for model in (Interaction, ITProduct, WorkflowStageRef, University, User):
            await session.execute(delete(model))
        await session.commit()
        await seed_reference(session)
    yield


async def _admin_token() -> str:
    async with SessionLocal() as session:
        user = User(
            email="admin-scope@rtk.ru",
            full_name="Админ",
            role=UserRole.ADMIN,
            is_admin=True,
            hashed_password=hash_password("secret123"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return create_access_token(user)


async def _university(name: str) -> int:
    async with SessionLocal() as session:
        university = University(name=name)
        session.add(university)
        await session.commit()
        await session.refresh(university)
        return university.id


async def _products(names: list[str]) -> list[int]:
    async with SessionLocal() as session:
        ids: list[int] = []
        for name in names:
            product = ITProduct(name=name)
            session.add(product)
            await session.flush()
            ids.append(product.id)
        await session.commit()
        return ids


async def _b2c_stage_id() -> int:
    async with SessionLocal() as session:
        return await session.scalar(
            select(WorkflowStageRef.id)
            .where(WorkflowStageRef.scope == WorkflowScope.B2C)
            .order_by(WorkflowStageRef.order)
        )


async def test_seed_creates_two_independent_workflows() -> None:
    async with SessionLocal() as session:
        stages = list(await session.scalars(select(WorkflowStageRef)))

    b2b = [s for s in stages if s.scope == WorkflowScope.B2B]
    b2c = [s for s in stages if s.scope == WorkflowScope.B2C]

    assert len(b2b) == len(WORKFLOW_STAGES) == 14
    assert len(b2c) == len(B2C_STAGES) == 4
    # Наборы этапов не пересекаются по коду — это две отдельные воронки.
    assert {s.code for s in b2b}.isdisjoint({s.code for s in b2c})


async def test_stages_endpoint_filters_by_scope() -> None:
    token = await _admin_token()
    async with _client() as client:
        response = await client.get(
            "/api/stages",
            params={"scope": "b2c"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == len(B2C_STAGES)
    assert all(stage["scope"] == "b2c" for stage in payload)


async def test_third_parallel_interaction_is_rejected() -> None:
    """У вуза допускается максимум 2 активных взаимодействия (409)."""
    token = await _admin_token()
    university_id = await _university("Лимит-Вуз")
    product_ids = await _products(["P1", "P2", "P3"])
    headers = {"Authorization": f"Bearer {token}"}

    async with _client() as client:
        statuses = []
        for product_id in product_ids:
            response = await client.post(
                "/api/interactions",
                json={
                    "university_id": university_id,
                    "product_id": product_id,
                    "scope": "b2b",
                },
                headers=headers,
            )
            statuses.append(response.status_code)
        detail = response.json()["detail"]

    assert statuses == [201, 201, 409]
    assert "Максимум" in detail


async def test_b2c_interaction_uses_b2c_stage_by_default() -> None:
    token = await _admin_token()
    university_id = await _university("B2C-Физлицо")

    async with _client() as client:
        response = await client.post(
            "/api/interactions",
            json={"university_id": university_id, "scope": "b2c"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["scope"] == "b2c"
    assert body["stage_code"] == B2C_STAGES[0][0]


async def test_stage_from_other_scope_is_rejected() -> None:
    token = await _admin_token()
    university_id = await _university("Скоуп-Вуз")
    b2c_stage_id = await _b2c_stage_id()

    async with _client() as client:
        response = await client.post(
            "/api/interactions",
            json={
                "university_id": university_id,
                "scope": "b2b",
                "stage_id": b2c_stage_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 409
    assert "другому workflow" in response.json()["detail"]


async def test_board_returns_only_requested_funnel() -> None:
    """Доска фильтруется по scope: карточки B2C не попадают в B2B-воронку."""
    token = await _admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    b2b_university = await _university("B2B-Вуз")
    b2c_university = await _university("B2C-Физлицо")

    async with _client() as client:
        await client.post(
            "/api/interactions",
            json={"university_id": b2b_university, "scope": "b2b"},
            headers=headers,
        )
        await client.post(
            "/api/interactions",
            json={"university_id": b2c_university, "scope": "b2c"},
            headers=headers,
        )

        b2b_board = (await client.get("/api/interactions/board", headers=headers)).json()
        b2c_board = (
            await client.get(
                "/api/interactions/board", params={"scope": "b2c"}, headers=headers
            )
        ).json()

    b2b_cards = [c for col in b2b_board["columns"] for c in col["interactions"]]
    b2c_cards = [c for col in b2c_board["columns"] for c in col["interactions"]]

    assert all(col["stage"]["scope"] == "b2b" for col in b2b_board["columns"])
    assert all(col["stage"]["scope"] == "b2c" for col in b2c_board["columns"])
    assert [c["university_name"] for c in b2b_cards] == ["B2B-Вуз"]
    assert [c["university_name"] for c in b2c_cards] == ["B2C-Физлицо"]


async def _b2b_stage_ids() -> list[int]:
    async with SessionLocal() as session:
        stages = list(
            await session.scalars(
                select(WorkflowStageRef)
                .where(WorkflowStageRef.scope == WorkflowScope.B2B)
                .order_by(WorkflowStageRef.order)
            )
        )
    return [stage.id for stage in stages]


async def test_reorder_stages_applies_full_permutation() -> None:
    """Перестановка крайних этапов проходит, несмотря на UNIQUE(scope, order)."""
    token = await _admin_token()
    ids = await _b2b_stage_ids()
    swapped = [ids[1], ids[0], *ids[2:]]

    async with _client() as client:
        response = await client.post(
            "/api/stages/reorder",
            json={
                "stages": [
                    {"id": stage_id, "order": position}
                    for position, stage_id in enumerate(swapped, start=1)
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200

    async with SessionLocal() as session:
        stages = list(
            await session.scalars(
                select(WorkflowStageRef).where(WorkflowStageRef.scope == WorkflowScope.B2B)
            )
        )

    orders = {stage.id: stage.order for stage in stages}
    assert [orders[stage_id] for stage_id in swapped] == list(range(1, len(swapped) + 1))
    assert sorted(orders.values()) == list(range(1, len(ids) + 1))


async def test_reorder_stages_keeps_unique_orders() -> None:
    """Итоговые порядки уникальны и не содержат временных отрицательных значений."""
    token = await _admin_token()
    ids = await _b2b_stage_ids()
    reversed_ids = list(reversed(ids))

    async with _client() as client:
        response = await client.post(
            "/api/stages/reorder",
            json={
                "stages": [
                    {"id": stage_id, "order": position}
                    for position, stage_id in enumerate(reversed_ids, start=1)
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200

    async with SessionLocal() as session:
        stages = list(
            await session.scalars(
                select(WorkflowStageRef).where(WorkflowStageRef.scope == WorkflowScope.B2B)
            )
        )

    orders = sorted(stage.order for stage in stages)
    assert orders == list(range(1, len(ids) + 1))


async def test_reorder_requires_admin() -> None:
    """Пересортировка недоступна обычному пользователю."""
    ids = await _b2b_stage_ids()
    async with SessionLocal() as session:
        user = User(
            email="user-reorder@rtk.ru",
            full_name="Пользователь",
            role=UserRole.USER,
            hashed_password=hash_password("secret123"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token(user)

    async with _client() as client:
        response = await client.post(
            "/api/stages/reorder",
            json={"stages": [{"id": ids[0], "order": 2}, {"id": ids[1], "order": 1}]},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403


async def _create_interaction(
    university_id: int, created_at: datetime | None = None
) -> int:
    """Создаёт взаимодействие с заданным created_at (для проверки фильтра дат)."""
    async with SessionLocal() as session:
        stage_id = await session.scalar(
            select(WorkflowStageRef.id)
            .where(WorkflowStageRef.scope == WorkflowScope.B2B)
            .order_by(WorkflowStageRef.order)
        )
        interaction = Interaction(
            university_id=university_id,
            stage_id=stage_id,
            scope=WorkflowScope.B2B,
            is_active=True,
        )
        if created_at is not None:
            interaction.created_at = created_at
        session.add(interaction)
        await session.commit()
        await session.refresh(interaction)
        return interaction.id


async def _board_card_names(params: dict, headers: dict) -> list[str]:
    async with _client() as client:
        board = (
            await client.get("/api/interactions/board", params=params, headers=headers)
        ).json()
    return [c["university_name"] for col in board["columns"] for c in col["interactions"]]


async def test_board_date_range_excludes_older_cards() -> None:
    """date_from отсекает карточки, созданные раньше начала диапазона."""
    token = await _admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    old_university = await _university("Старый-Вуз")
    new_university = await _university("Новый-Вуз")
    now = datetime.now(UTC)
    await _create_interaction(old_university, now - timedelta(days=40))
    await _create_interaction(new_university, now - timedelta(days=2))

    names = await _board_card_names(
        {"date_from": (now - timedelta(days=7)).date().isoformat()}, headers
    )

    assert names == ["Новый-Вуз"]


async def test_board_date_range_includes_whole_end_day() -> None:
    """date_to включает весь последний день, а не только 00:00."""
    token = await _admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    university = await _university("Вечерний-Вуз")
    # 23:00 того же дня, что и date_to — карточка должна попасть в выборку.
    target_day = (datetime.now(UTC) - timedelta(days=3)).date()
    await _create_interaction(
        university, datetime.combine(target_day, time(23, 0), tzinfo=UTC)
    )

    names = await _board_card_names(
        {"date_from": target_day.isoformat(), "date_to": target_day.isoformat()},
        headers,
    )

    assert names == ["Вечерний-Вуз"]


async def test_board_date_range_excludes_later_cards() -> None:
    """date_to отсекает карточки, созданные позже конца диапазона."""
    token = await _admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    university = await _university("Поздний-Вуз")
    now = datetime.now(UTC)
    await _create_interaction(university, now)

    names = await _board_card_names(
        {"date_to": (now - timedelta(days=10)).date().isoformat()}, headers
    )

    assert names == []


async def test_board_rejects_inverted_date_range() -> None:
    """Перевёрнутый диапазон отклоняется 400 — контракт как в отчётах."""
    token = await _admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with _client() as client:
        response = await client.get(
            "/api/interactions/board",
            params={"date_from": "2026-09-29", "date_to": "2026-09-01"},
            headers=headers,
        )

    assert response.status_code == 400
    assert "позже" in response.json()["detail"]

