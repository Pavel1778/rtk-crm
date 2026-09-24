"""Тесты идемпотентной сверки схемы БД и корневого роута сервиса.

Прод-база была создана ранней версией `create_all()`: без `scope` в
`workflow_stages`/`interactions` и с глобальной уникальностью по `code`/
`order`. Такие тесты воспроизводят эту схему и проверяют, что `ensure_schema`
приводит её к моделям, сохраняя данные.
"""

from __future__ import annotations

import pytest
from app.db.schema_sync import _apply
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, inspect, text

# Схема «как на проде» до внедрения scope: глобальные UNIQUE по code/order.
_LEGACY_DDL = """
CREATE TABLE workflow_stages (
  id INTEGER NOT NULL PRIMARY KEY,
  code VARCHAR(50) NOT NULL,
  name VARCHAR(255) NOT NULL,
  "order" INTEGER NOT NULL,
  color VARCHAR(20),
  is_active BOOLEAN NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
  UNIQUE (code), UNIQUE ("order")
);
CREATE TABLE interactions (
  id INTEGER NOT NULL PRIMARY KEY,
  university_id INTEGER NOT NULL,
  stage_id INTEGER NOT NULL,
  contract_number VARCHAR(100),
  is_active BOOLEAN NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE TABLE attached_files (
  id INTEGER NOT NULL PRIMARY KEY,
  interaction_id INTEGER NOT NULL,
  filename VARCHAR(255) NOT NULL,
  file_path VARCHAR(500) NOT NULL,
  size INTEGER NOT NULL,
  mime_type VARCHAR(100) NOT NULL,
  uploaded_by INTEGER NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
CREATE TABLE action_logs (
  id INTEGER NOT NULL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  action VARCHAR(50) NOT NULL,
  entity_type VARCHAR(50) NOT NULL,
  entity_id INTEGER NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);
"""


@pytest.fixture
def legacy_engine(tmp_path):
    """SQLite с legacy-схемой и данными, которые нельзя потерять."""
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as conn:
        for stmt in _LEGACY_DDL.strip().split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
        conn.execute(
            text(
                "INSERT INTO workflow_stages (code, name, \"order\", is_active) "
                "VALUES ('contact_search', 'Поиск контактов', 1, 1), "
                "('communication', 'Коммуникация', 2, 1)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO interactions "
                "(university_id, stage_id, contract_number, is_active) "
                "VALUES (10, 1, 'Д-1', 1), (11, 2, 'Д-2', 1)"
            )
        )
    yield engine
    engine.dispose()


def test_schema_sync_adds_scope_columns(legacy_engine) -> None:
    """Колонки scope добавляются в обе таблицы с дефолтом b2b."""
    with legacy_engine.begin() as conn:
        applied = _apply(conn)

    assert "workflow_stages.scope" in applied
    assert "interactions.scope" in applied

    insp = inspect(legacy_engine)
    assert "scope" in {c["name"] for c in insp.get_columns("workflow_stages")}
    assert "scope" in {c["name"] for c in insp.get_columns("interactions")}

    with legacy_engine.connect() as conn:
        rows = conn.execute(text("SELECT DISTINCT scope FROM interactions")).fetchall()
    assert rows == [("b2b",)]


def test_schema_sync_replaces_global_unique_with_scoped(legacy_engine) -> None:
    """Глобальные UNIQUE(code)/UNIQUE(order) заменяются на составные по scope."""
    with legacy_engine.begin() as conn:
        _apply(conn)

    uniques = {
        tuple(u["column_names"]): u["name"]
        for u in inspect(legacy_engine).get_unique_constraints("workflow_stages")
    }
    assert set(uniques) == {("scope", "code"), ("scope", "order")}
    assert uniques[("scope", "code")] == "uq_workflow_stages_scope_code"
    assert uniques[("scope", "order")] == "uq_workflow_stages_scope_order"


def test_schema_sync_preserves_existing_data(legacy_engine) -> None:
    """Пересоздание таблицы не теряет строки и значения существующих колонок."""
    with legacy_engine.begin() as conn:
        _apply(conn)

    with legacy_engine.connect() as conn:
        stages = conn.execute(
            text("SELECT id, code, scope, name FROM workflow_stages ORDER BY id")
        ).fetchall()
        interactions = conn.execute(
            text(
                "SELECT id, university_id, contract_number, scope "
                "FROM interactions ORDER BY id"
            )
        ).fetchall()

    assert [tuple(row) for row in stages] == [
        (1, "contact_search", "b2b", "Поиск контактов"),
        (2, "communication", "b2b", "Коммуникация"),
    ]
    assert [tuple(row) for row in interactions] == [
        (1, 10, "Д-1", "b2b"),
        (2, 11, "Д-2", "b2b"),
    ]


def test_schema_sync_is_idempotent(legacy_engine) -> None:
    """Повторный запуск ничего не меняет: миграция безопасна при рестартах."""
    with legacy_engine.begin() as conn:
        first = _apply(conn)
    with legacy_engine.begin() as conn:
        second = _apply(conn)

    assert first
    assert second == []


def test_schema_sync_allows_same_code_in_other_scope(legacy_engine) -> None:
    """B2C-этап с тем же кодом, что у B2B, разрешён составной уникальностью."""
    with legacy_engine.begin() as conn:
        _apply(conn)
        conn.execute(
            text(
                "INSERT INTO workflow_stages (code, scope, name, \"order\", is_active) "
                "VALUES ('contact_search', 'b2c', 'b2c-этап', 1, 1)"
            )
        )
        total = conn.execute(text("SELECT COUNT(*) FROM workflow_stages")).scalar()

    assert total == 3


def test_schema_sync_relaxes_not_null_user_fks(legacy_engine) -> None:
    """NOT NULL на FK к users снимается: иначе удаление пользователя падает."""
    with legacy_engine.begin() as conn:
        _apply(conn)

    insp = inspect(legacy_engine)
    files = {c["name"]: c for c in insp.get_columns("attached_files")}
    logs = {c["name"]: c for c in insp.get_columns("action_logs")}
    assert files["uploaded_by"]["nullable"] is True
    assert logs["user_id"]["nullable"] is True


def test_schema_sync_nullable_rewrite_is_idempotent(legacy_engine) -> None:
    """Повторная сверка после снятия NOT NULL больше ничего не меняет."""
    with legacy_engine.begin() as conn:
        first = _apply(conn)
    with legacy_engine.begin() as conn:
        second = _apply(conn)
    assert first
    assert second == []



def test_schema_sync_rejects_duplicate_in_same_scope(legacy_engine) -> None:
    """Дубль (scope, code) в пределах одного scope отвергается."""
    from sqlalchemy.exc import IntegrityError

    with legacy_engine.begin() as conn:
        _apply(conn)

    with pytest.raises(IntegrityError), legacy_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO workflow_stages "
                "(code, scope, name, \"order\", is_active) "
                "VALUES ('contact_search', 'b2b', 'дубль', 99, 1)"
            )
        )


async def test_root_returns_service_hints() -> None:
    """Корень сервиса отдаёт ссылки, а не 404 для открывших URL без пути."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["docs"] == "/docs"
    assert body["health"] == "/healthz"
    assert body["ready"] == "/readyz"
