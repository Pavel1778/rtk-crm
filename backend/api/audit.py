"""Чтение журнала аудита действий (152-ФЗ).

Записи создаёт middleware `app.middleware.audit` на каждую успешную
мутацию. Отдельный read-эндпоинт нужен, чтобы журнал можно было
показать администратору — иначе данные копятся в БД, но недоступны.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import require_admin
from app.db.session import get_db
from app.models.entities import ActionLog, User
from app.schemas.entities import AuditLogPage, AuditLogRead

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _as_utc(value: datetime) -> datetime:
    """Naive-дату из query трактуем как UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.get("", response_model=AuditLogPage)
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
    action: str | None = Query(default=None, description="CREATE/UPDATE/DELETE"),
    entity_type: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AuditLogPage:
    """Последние действия по фильтрам, свежие сверху."""
    filters = []
    if action:
        filters.append(ActionLog.action == action.upper())
    if entity_type:
        filters.append(ActionLog.entity_type == entity_type)
    if user_id is not None:
        filters.append(ActionLog.user_id == user_id)
    if date_from is not None:
        # Колонка TIMESTAMP WITH TIME ZONE; naive-значение из query
        # сравниваем как UTC, иначе Postgres отвергает сравнение.
        filters.append(ActionLog.created_at >= _as_utc(date_from))
    if date_to is not None:
        filters.append(ActionLog.created_at <= _as_utc(date_to))

    total = await db.scalar(
        select(func.count(ActionLog.id)).where(*filters)
    )
    rows = (
        await db.execute(
            select(ActionLog, User.full_name)
            .outerjoin(User, ActionLog.user_id == User.id)
            .where(*filters)
            .order_by(desc(ActionLog.created_at), desc(ActionLog.id))
            .limit(limit)
            .offset(offset)
        )
    ).all()

    return AuditLogPage(
        total=total or 0,
        items=[
            AuditLogRead(
                id=entry.id,
                user_id=entry.user_id,
                user_name=user_name,
                action=entry.action,
                entity_type=entry.entity_type,
                entity_id=entry.entity_id,
                ip_address=entry.ip_address,
                new_value=entry.new_value,
                created_at=entry.created_at,
            )
            for entry, user_name in rows
        ],
    )


@router.get("/entity-types", response_model=list[str])
async def list_entity_types(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[str]:
    """Справочник типов сущностей для фильтра в интерфейсе."""
    result = await db.scalars(
        select(ActionLog.entity_type).distinct().order_by(ActionLog.entity_type)
    )
    return [value for value in result if value]
