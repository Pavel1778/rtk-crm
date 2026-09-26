"""Тесты интеграции с LMS и CMS (ФТ-5).

Проверяются реальные пути: разбор входящего пакета, dry-run без записи,
импорт в workflow, сопоставление по номеру договора и исходящий пакет.
"""

from __future__ import annotations

import pytest
from app.auth.security import hash_password
from app.db.session import SessionLocal, create_tables
from app.main import app
from app.models.entities import (
    Action,
    AttachedFile,
    Comment,
    Interaction,
    ITDirection,
    ITProduct,
    University,
    User,
    WorkflowStageRef,
)
from app.models.enums import UserRole
from app.seed import seed_reference
from app.services.integration import parse_payload
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
            Comment,
            Action,
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
        # Вузы создаются явно: seed_reference наполняет только справочники,
        # а импорт сопоставляет записи именно по названию вуза.
        for name, city in (
            ("МГТУ им. Н. Э. Баумана", "Москва"),
            ("ИТМО", "Санкт-Петербург"),
            ("Университет ИТЭГ", "Казань"),
            ("НГУ", "Новосибирск"),
            ("МГУ им. М. В. Ломоносова", "Москва"),
        ):
            session.add(University(name=name, city=city))
        await session.commit()
    yield


async def _token(role: UserRole = UserRole.ADMIN) -> str:
    from app.auth.security import create_access_token

    async with SessionLocal() as session:
        user = User(
            email=f"integration-{role.value}@rtk.ru",
            full_name="Интегратор",
            role=role,
            is_admin=role == UserRole.ADMIN,
            hashed_password=hash_password("secret123"),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return create_access_token(user)


# ---------- Разбор пакета (юнит) ----------


def test_parse_accepts_items_object():
    parsed = parse_payload({"items": [{"external_id": "1", "university": "МГТУ"}]})
    assert len(parsed.records) == 1
    assert parsed.records[0].external_id == "1"
    assert not parsed.errors


def test_parse_accepts_bare_list():
    parsed = parse_payload([{"external_id": "1", "university": "МГТУ"}])
    assert len(parsed.records) == 1


def test_parse_skips_null_without_error():
    """null внутри массива — реальный случай в выгрузках заказчика."""
    parsed = parse_payload(
        [None, {"external_id": "2", "university": "ИТМО"}]
    )
    assert len(parsed.records) == 1
    assert not parsed.errors
    assert any("пустое значение" in warning for warning in parsed.warnings)


def test_parse_reports_missing_required_fields():
    parsed = parse_payload([{"external_id": "1"}, {"university": "МГТУ"}])
    assert not parsed.records
    assert len(parsed.errors) == 2


def test_parse_normalizes_unknown_scope():
    parsed = parse_payload(
        [{"external_id": "1", "university": "МГТУ", "scope": "b2x"}]
    )
    assert parsed.records[0].scope == "b2b"
    assert any("scope" in warning for warning in parsed.warnings)


def test_parse_collects_unknown_fields():
    parsed = parse_payload(
        [{"external_id": "1", "university": "МГТУ", "unexpected": "x"}]
    )
    assert "unexpected" in parsed.unknown_fields


# ---------- API ----------


async def test_schema_endpoint_lists_fields():
    token = await _token()
    async with _client() as client:
        response = await client.get(
            "/api/integration/schema",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert "external_id" in body["required"]
    assert "university" in body["required"]
    assert set(body["scope_values"]) == {"b2b", "b2c"}


async def test_preview_does_not_write():
    token = await _token()
    payload = {
        "items": [
            {"external_id": "LMS-1", "university": "МГТУ им. Н. Э. Баумана"},
        ]
    }
    async with _client() as client:
        response = await client.post(
            "/api/integration/preview",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    assert response.json()["total"] == 1

    async with SessionLocal() as session:
        count = await session.scalar(select(Interaction).where(
            Interaction.contract_number == "LMS-1"
        ))
    assert count is None


async def test_import_creates_interaction():
    token = await _token()
    payload = [
        {
            "external_id": "LMS-1",
            "university": "МГТУ им. Н. Э. Баумана",
            "product": "RUBOTYAKA",
            "stage_code": "meeting",
            "contract_number": "LMS-2026/1",
            "university_specialist": "Иванов И. И.",
        }
    ]
    async with _client() as client:
        response = await client.post(
            "/api/integration/import",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1
    assert body["skipped"] == 0

    async with SessionLocal() as session:
        interaction = await session.scalar(
            select(Interaction).where(Interaction.contract_number == "LMS-2026/1")
        )
        assert interaction is not None
        assert interaction.university_specialist == "Иванов И. И."
        stage = await session.get(WorkflowStageRef, interaction.stage_id)
        assert stage.code == "meeting"


async def test_import_is_idempotent_by_contract_number():
    token = await _token()
    payload = [
        {
            "external_id": "LMS-9",
            "university": "ИТМО",
            "contract_number": "LMS-2026/9",
            "notes": "первый прогон",
        }
    ]
    async with _client() as client:
        first = await client.post(
            "/api/integration/import",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        payload[0]["notes"] = "второй прогон"
        second = await client.post(
            "/api/integration/import",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert first.json()["created"] == 1
    assert second.json()["updated"] == 1
    assert second.json()["created"] == 0

    async with SessionLocal() as session:
        rows = list(
            await session.scalars(
                select(Interaction).where(Interaction.contract_number == "LMS-2026/9")
            )
        )
    assert len(rows) == 1
    assert rows[0].notes == "второй прогон"


async def test_import_unknown_university_is_reported():
    token = await _token()
    payload = [{"external_id": "X-1", "university": "Несуществующий ВУЗ"}]
    async with _client() as client:
        response = await client.post(
            "/api/integration/import",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
    body = response.json()
    assert body["created"] == 0
    assert body["skipped"] == 1
    assert "не найден" in body["errors"][0]


async def test_pull_stub_lms_and_cms():
    token = await _token()
    async with _client() as client:
        lms = await client.get(
            "/api/integration/pull/lms",
            headers={"Authorization": f"Bearer {token}"},
        )
        cms = await client.get(
            "/api/integration/pull/cms",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert lms.status_code == 200
    assert lms.json()["created"] == 2
    assert cms.status_code == 200
    assert cms.json()["created"] == 2


async def test_pull_unknown_source_returns_404():
    token = await _token()
    async with _client() as client:
        response = await client.get(
            "/api/integration/pull/unknown",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 404


async def test_outbound_package_has_links_and_files():
    token = await _token()
    async with _client() as client:
        await client.get(
            "/api/integration/pull/lms",
            headers={"Authorization": f"Bearer {token}"},
        )
        response = await client.get(
            "/api/integration/outbound",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["direction"] == "crm->external"
    assert body["total"] == 2
    item = body["items"][0]
    for key in ("id", "university_id", "stage_id", "files"):
        assert key in item


async def test_import_requires_manager_role():
    """Обычный КАМ не имеет права запускать интеграционный импорт."""
    token = await _token(UserRole.USER)
    async with _client() as client:
        response = await client.post(
            "/api/integration/import",
            json=[{"external_id": "1", "university": "МГТУ им. Н. Э. Баумана"}],
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 403
