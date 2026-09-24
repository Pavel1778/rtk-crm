"""Идемпотентная сверка схемы БД с моделями.

Прод-база создавалась ранней версией `create_all()`: тогда `workflow_stages`
не имел `scope`, а уникальность задавалась глобально по `code` и `order`.
`create_all(checkfirst=True)` существующие таблицы не меняет, поэтому старая
схема молча оставалась «как есть», и загрузка демо-данных падала с
`column workflow_stages.scope does not exist`.

Модуль приводит уже существующую схему к текущим моделям: добавляет
недостающие колонки и индексы, заменяет устаревшие глобальные уникальные
ограничения на составные `(scope, code)` и `(scope, order)`. Операция
идемпотентна и повторяемый запуск ничего не ломает; данные не удаляются,
новые колонки получают `DEFAULT 'b2b'`.
"""

from __future__ import annotations

import re
from pathlib import Path

from loguru import logger
from sqlalchemy import MetaData, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.schema import CreateIndex, CreateTable

# Колонки, которые должны существовать в таблице. DDL подставляется как есть,
# поэтому выражение обязано подходить и SQLite, и Postgres.
_REQUIRED_COLUMNS: dict[str, dict[str, str]] = {
    "workflow_stages": {"scope": "VARCHAR(10) NOT NULL DEFAULT 'b2b'"},
    "interactions": {"scope": "VARCHAR(10) NOT NULL DEFAULT 'b2b'"},
}

# Индексы, которые должны существовать. Ключ — имя, значение — таблица и колонки.
_REQUIRED_INDEXES: dict[str, tuple[str, tuple[str, ...]]] = {
    "ix_workflow_stages_scope_order": ("workflow_stages", ("scope", "order")),
    "ix_interactions_scope": ("interactions", ("scope",)),
}

# Колонки, которые обязаны допускать NULL. FK на `users.id` объявлены с
# ondelete="SET NULL", поэтому NOT NULL в старой схеме ломает удаление
# пользователя: Postgres пытается обнулить ссылку и нарушает ограничение.
_REQUIRED_NULLABLE: dict[str, tuple[str, ...]] = {
    "attached_files": ("uploaded_by",),
    "action_logs": ("user_id",),
}

# Устаревшая глобальная уникальность и её замена на составную по scope.
# Ключ — таблица, значение — список пар: (старые колонки, новые колонки).
_UNIQUE_REWRITE: dict[str, list[tuple[tuple[str, ...], tuple[str, ...]]]] = {
    "workflow_stages": [
        (("code",), ("scope", "code")),
        (("order",), ("scope", "order")),
    ],
}

# Имена составных ограничений совпадают с моделями, чтобы Alembic-autogenerate
# не видел расхождений после сверки.
_COMPOSITE_UNIQUE_NAMES: dict[tuple[str, tuple[str, ...]], str] = {
    ("workflow_stages", ("scope", "code")): "uq_workflow_stages_scope_code",
    ("workflow_stages", ("scope", "order")): "uq_workflow_stages_scope_order",
}


def _unique_maps(insp, table: str) -> dict[tuple[str, ...], str | None]:
    """Уникальные ограничения таблицы: набор колонок -> имя (может быть None)."""
    return {
        tuple(row["column_names"]): row.get("name")
        for row in insp.get_unique_constraints(table)
    }


def _index_names(insp, table: str) -> set[str]:
    return {row["name"] for row in insp.get_indexes(table) if row.get("name")}


def _rebuild_sqlite(conn: Connection, table: str) -> None:
    """Пересоздаёт таблицу по модели: SQLite не умеет DROP CONSTRAINT.

    Копируем данные по общим колонкам, поэтому состав таблицы в прод-БД
    (старее модели) не теряется: новых колонок станет больше, но строки и
    значения существующих колонок сохраняются.
    """
    import app.models  # noqa: F401  регистрирует модели в Base.metadata
    from app.db.base import Base

    model_table = Base.metadata.tables[table]
    existing_cols = {row["name"] for row in inspect(conn).get_columns(table)}
    tmp = f"{table}__schema_sync"

    # Временный MetaData должен содержать таблицы, на которые ссылаются FK
    # пересоздаваемой таблицы: иначе CreateTable не соберёт DDL.
    tmp_metadata = MetaData()
    referenced: set[str] = set()
    pending = [fk.target_fullname.split(".")[0] for fk in model_table.foreign_keys]
    while pending:
        name = pending.pop()
        if name in referenced or name == table or name not in Base.metadata.tables:
            continue
        referenced.add(name)
        pending.extend(
            fk.target_fullname.split(".")[0]
            for fk in Base.metadata.tables[name].foreign_keys
        )
    for name in sorted(referenced):
        Base.metadata.tables[name].to_metadata(tmp_metadata)

    tmp_table = model_table.to_metadata(tmp_metadata, name=tmp)
    conn.execute(text(f'DROP TABLE IF EXISTS "{tmp}"'))
    conn.execute(CreateTable(tmp_table))
    for index in tmp_table.indexes:
        conn.execute(CreateIndex(index))

    common = [c.name for c in model_table.columns if c.name in existing_cols]
    columns = ", ".join(f'"{name}"' for name in common)
    conn.execute(
        text(f'INSERT INTO "{tmp}" ({columns}) SELECT {columns} FROM "{table}"')
    )
    conn.execute(text(f'DROP TABLE "{table}"'))
    # В SQLite RENAME TO переносит индексы на новое имя таблицы, сохраняя
    # их имена, поэтому составные ограничения остаются в нужной форме.
    conn.execute(text(f'ALTER TABLE "{tmp}" RENAME TO "{table}"'))


def _rewrite_uniques(conn: Connection, insp, table: str) -> list[str]:
    """Снимает устаревшие глобальные уникальности, ставит составные по scope."""
    applied: list[str] = []
    current = _unique_maps(insp, table)
    pending = [
        (old, new)
        for old, new in _UNIQUE_REWRITE.get(table, [])
        if old in current and new not in current
    ]
    if not pending:
        return applied

    if conn.dialect.name == "sqlite":
        _rebuild_sqlite(conn, table)
        # Пересоздание уже подтянуло составные ограничения из модели.
        applied.extend(f"{table}({','.join(new)})" for _, new in pending)
        return applied

    for old, new in pending:
        name = current[old]
        if name:
            conn.execute(text(f'ALTER TABLE "{table}" DROP CONSTRAINT "{name}"'))
        constraint = _COMPOSITE_UNIQUE_NAMES.get((table, new))
        columns = ", ".join(f'"{col}"' for col in new)
        clause = f'CONSTRAINT "{constraint}" ' if constraint else ""
        conn.execute(
            text(f'ALTER TABLE "{table}" ADD {clause}UNIQUE ({columns})')
        )
        applied.append(f"{table}({','.join(new)})")
    return applied


def _nullable_relaxed(conn: Connection, insp, table: str) -> list[str]:
    """Снимает NOT NULL с колонок, которые по модели допускают NULL."""
    applied: list[str] = []
    columns = _REQUIRED_NULLABLE.get(table)
    if not columns or not insp.has_table(table):
        return applied

    actual = {row["name"]: row for row in insp.get_columns(table)}
    to_relax = [
        name
        for name in columns
        if name in actual and not actual[name].get("nullable", True)
    ]
    if not to_relax:
        return applied

    if conn.dialect.name == "sqlite":
        # SQLite не умеет ALTER COLUMN: пересоздаём таблицу по модели.
        _rebuild_sqlite(conn, table)
        return [f"{table}.{name} NULL" for name in to_relax]

    for name in to_relax:
        conn.execute(text(f'ALTER TABLE "{table}" ALTER COLUMN "{name}" DROP NOT NULL'))
        applied.append(f"{table}.{name} NULL")
    return applied


def _apply(conn: Connection) -> list[str]:
    insp = inspect(conn)
    applied: list[str] = []

    for table, required in _REQUIRED_COLUMNS.items():
        if not insp.has_table(table):
            continue
        existing = {row["name"] for row in insp.get_columns(table)}
        for column, ddl in required.items():
            if column in existing:
                continue
            conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN {column} {ddl}'))
            applied.append(f"{table}.{column}")

    for table in _REQUIRED_NULLABLE:
        applied.extend(_nullable_relaxed(conn, insp, table))

    for table in _UNIQUE_REWRITE:
        if insp.has_table(table):
            applied.extend(_rewrite_uniques(conn, insp, table))

    for name, (table, index_columns) in _REQUIRED_INDEXES.items():
        if not insp.has_table(table) or name in _index_names(insp, table):
            continue
        cols = ", ".join(f'"{col}"' for col in index_columns)
        conn.execute(text(f'CREATE INDEX IF NOT EXISTS "{name}" ON "{table}" ({cols})'))
        applied.append(name)

    return applied


async def ensure_schema() -> list[str]:
    """Сверяет схему с моделями и возвращает список применённых изменений."""
    from app.db.session import engine

    async with engine.begin() as conn:
        applied = await conn.run_sync(_apply)

    if applied:
        logger.info(f"Схема БД обновлена: {', '.join(applied)}")
    else:
        logger.info("Схема БД соответствует моделям")

    await _stamp_alembic_head()
    return applied


def _head_revision() -> str | None:
    """Идентификатор головной ревизии из каталога `alembic/versions`.

    В образе (`/app`) каталог лежит рядом с модулем, поэтому определяем его
    от расположения файла, а не от `alembic.ini` в корне репозитория.
    """
    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    if not versions.is_dir():
        return None

    revisions: dict[str, str | None] = {}
    for path in versions.glob("*.py"):
        text_module = path.read_text(encoding="utf-8")
        revision = re.search(r"^revision:\s*str\s*=\s*['\"]([^'\"]+)", text_module, re.M)
        down = re.search(
            r"^down_revision[^=]*=\s*(?:['\"]([^'\"]+)['\"]|None)", text_module, re.M
        )
        if revision:
            revisions[revision.group(1)] = down.group(1) if down else None

    parents = {down for down in revisions.values() if down}
    heads = [rev for rev in revisions if rev not in parents]
    return heads[0] if len(heads) == 1 else None


async def _stamp_alembic_head() -> None:
    """Отмечает в alembic_version головную ревизию, если её там ещё нет.

    Схема доведена до моделей вручную, а Alembic-миграция в прод-базе не
    применялась (её таблица пуста). Без штампа последующий
    `alembic upgrade head` попытался бы создать уже существующие таблицы.
    Ошибка здесь не критична: штатный запуск от неё не зависит.
    """
    head = _head_revision()
    if head is None:
        return

    from app.db.session import engine

    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS alembic_version ("
                    "version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                )
            )
            current = await conn.scalar(text("SELECT version_num FROM alembic_version"))
            if current == head:
                return
            await conn.execute(text("DELETE FROM alembic_version"))
            await conn.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:rev)"),
                {"rev": head},
            )
        logger.info(f"Alembic отмечен ревизией {head}")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Не удалось проставить ревизию Alembic: {exc}")
