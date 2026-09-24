"""Тесты отчёта: разделение воронок B2B и B2C.

Отчёт не должен смешивать этапы обеих воронок: набор этапов, график
распределения и выгрузки фильтруются по scope так же, как доска.
"""

from __future__ import annotations

import pytest
from app.auth.security import create_access_token, hash_password
from app.db.session import SessionLocal, create_tables
from app.main import app
from app.models.entities import (
    Action,
    Interaction,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)
from app.models.enums import B2C_STAGES, UserRole
from app.seed import WORKFLOW_STAGES, seed_reference
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
async def _prepare_db():
    await create_tables()
    async with SessionLocal() as session:
        for model in (Action, Interaction, ITProduct, WorkflowStageRef, University, User):
            await session.execute(delete(model))
        await session.commit()
        await seed_reference(session)
    yield


async def _admin_token() -> str:
    async with SessionLocal() as session:
        user = User(
            email="admin-report@rtk.ru",
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


async def test_report_actions_follow_scope() -> None:
    """Счётчики задач относятся только к взаимодействиям выбранной воронки."""
    token = await _admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    b2b_university = await _university("B2B-Вуз")
    b2c_university = await _university("B2C-Физлицо")

    async with _client() as client:
        b2b_resp = await client.post(
            "/api/interactions",
            json={"university_id": b2b_university, "scope": "b2b"},
            headers=headers,
        )
        b2c_resp = await client.post(
            "/api/interactions",
            json={"university_id": b2c_university, "scope": "b2c"},
            headers=headers,
        )

    b2b_id = b2b_resp.json()["id"]
    b2c_id = b2c_resp.json()["id"]
    async with SessionLocal() as session:
        session.add(Action(interaction_id=b2b_id, title="Задача B2B", is_completed=False))
        session.add(Action(interaction_id=b2b_id, title="Закрытая B2B", is_completed=True))
        session.add(Action(interaction_id=b2c_id, title="Задача B2C", is_completed=False))
        await session.commit()

    async with _client() as client:
        b2b = (
            await client.get("/api/reports", params={"scope": "b2b"}, headers=headers)
        ).json()
        b2c = (
            await client.get("/api/reports", params={"scope": "b2c"}, headers=headers)
        ).json()

    def metric(report: dict, key: str) -> int:
        return next(m for m in report["metrics"] if m["key"] == key)["value"]

    assert metric(b2b, "actions_open") == 1
    assert metric(b2b, "actions_done") == 1
    assert metric(b2c, "actions_open") == 1
    assert metric(b2c, "actions_done") == 0


async def test_report_stage_list_follows_scope() -> None:
    """by_stage и stage_progress содержат только этапы выбранной воронки."""
    token = await _admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with _client() as client:
        b2b = (
            await client.get("/api/reports", params={"scope": "b2b"}, headers=headers)
        ).json()
        b2c = (
            await client.get("/api/reports", params={"scope": "b2c"}, headers=headers)
        ).json()

    assert len(b2b["by_stage"]) == len(WORKFLOW_STAGES) == 14
    assert len(b2c["by_stage"]) == len(B2C_STAGES) == 4
    b2b_names = {stage["name"] for stage in b2b["by_stage"]}
    b2c_names = {stage["name"] for stage in b2c["by_stage"]}
    assert b2b_names.isdisjoint(b2c_names)
    # График распределения использует тот же набор этапов.
    assert [p["stage_name"] for p in b2b["stage_progress"]] == [
        s["name"] for s in b2b["by_stage"]
    ]


async def test_report_counts_only_selected_funnel() -> None:
    """Карточка B2C не попадает в метрики B2B-отчёта и наоборот."""
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
        b2b = (
            await client.get("/api/reports", params={"scope": "b2b"}, headers=headers)
        ).json()
        b2c = (
            await client.get("/api/reports", params={"scope": "b2c"}, headers=headers)
        ).json()

    b2b_total = next(m for m in b2b["metrics"] if m["key"] == "interactions")["value"]
    b2c_total = next(m for m in b2c["metrics"] if m["key"] == "interactions")["value"]
    assert b2b_total == 1
    assert b2c_total == 1
    assert b2b["metrics"] != b2c["metrics"] or b2b_total == b2c_total


async def test_report_preview_and_json_export_respect_scope() -> None:
    """Предпросмотр и JSON-выгрузка не смешивают воронки."""
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
        preview = (
            await client.get(
                "/api/reports/preview", params={"scope": "b2c"}, headers=headers
            )
        ).json()
        exported = (
            await client.get(
                "/api/reports/json", params={"scope": "b2b"}, headers=headers
            )
        ).json()

    assert [row["university_name"] for row in preview] == ["B2C-Физлицо"]
    assert all(row["scope"] == "b2c" for row in preview)
    assert [item["university_name"] for item in exported["interactions"]] == ["B2B-Вуз"]
    assert exported["filters"]["scope"] == "b2b"


async def test_report_cache_separates_funnels() -> None:
    """Кэш не отдаёт сводку B2B на запрос B2C с теми же фильтрами."""
    token = await _admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    university_id = await _university("Кэш-Вуз")

    async with _client() as client:
        await client.post(
            "/api/interactions",
            json={"university_id": university_id, "scope": "b2b"},
            headers=headers,
        )
        # Первый запрос прогревает кэш, второй должен получить свою воронку.
        b2b = (
            await client.get("/api/reports", params={"scope": "b2b"}, headers=headers)
        ).json()
        b2c = (
            await client.get("/api/reports", params={"scope": "b2c"}, headers=headers)
        ).json()

    assert len(b2b["by_stage"]) == 14
    assert len(b2c["by_stage"]) == 4
    assert b2c["by_stage"][0]["name"] == B2C_STAGES[0][1]


async def test_report_scope_defaults_to_all_funnels() -> None:
    """Без scope отчёт сохраняет прежнее поведение (обе воронки вместе)."""
    token = await _admin_token()
    async with _client() as client:
        response = await client.get(
            "/api/reports", headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    assert len(response.json()["by_stage"]) == len(WORKFLOW_STAGES) + len(B2C_STAGES)
