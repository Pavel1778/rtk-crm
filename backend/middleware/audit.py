"""Middleware для аудита действий (152-ФЗ)."""

import json
from collections.abc import Callable
from contextlib import suppress

from app.db.session import SessionLocal
from app.models.entities import ActionLog
from fastapi import Request, Response


async def audit_middleware(request: Request, call_next: Callable) -> Response:
    """Логирование POST/PUT/PATCH/DELETE запросов."""

    # Пропускаем GET и OPTIONS запросы
    if request.method in ["GET", "OPTIONS", "HEAD"]:
        return await call_next(request)

    # Пропускаем эндпоинты логина и health
    if request.url.path in ["/api/auth/login", "/api/health", "/health"]:
        return await call_next(request)

    # Сохраняем тело запроса для логирования
    body = await request.body()

    # Выполняем запрос
    response = await call_next(request)

    # Логируем только успешные запросы
    if response.status_code < 400:
        # Ошибка логирования не должна прерывать запрос пользователя.
        with suppress(Exception):
            # Получаем пользователя из контекста (если есть)
            user = getattr(request.state, "user", None)
            user_id = user.id if user else None

            # Определяем тип сущности и ID из пути
            entity_type, entity_id = _parse_entity_from_path(request.url.path)

            if entity_type:
                # Определяем действие
                action_map = {
                    "POST": "CREATE",
                    "PUT": "UPDATE",
                    "PATCH": "UPDATE",
                    "DELETE": "DELETE",
                }
                action = action_map.get(request.method, request.method)

                # Получаем IP адрес
                ip_address = request.client.host if request.client else None

                # Логируем в БД
                async with SessionLocal() as session:
                    # Ограничиваем размер тела для логирования
                    body_str = _safe_body(body)

                    log_entry = ActionLog(
                        user_id=user_id,
                        action=action,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        new_value=body_str,
                        ip_address=ip_address,
                    )
                    session.add(log_entry)
                    await session.commit()

    return response


def _parse_entity_from_path(path: str) -> tuple[str | None, int | None]:
    """Парсит путь и возвращает тип сущности и ID."""
    # Примеры путей:
    # /api/interactions/123 -> ("Interaction", 123)
    # /api/universities/456 -> ("University", 456)
    # /api/files/789 -> ("AttachedFile", 789)

    parts = path.strip("/").split("/")
    if len(parts) >= 2:
        entity_name = parts[1]
        entity_map = {
            "interactions": "Interaction",
            "universities": "University",
            "files": "AttachedFile",
            "actions": "Action",
            "comments": "Comment",
            "stages": "WorkflowStageRef",
            "products": "ITProduct",
            "directions": "ITDirection",
            "catalogs": "Catalog",
            "reports": "Report",
        }
        entity_type = entity_map.get(entity_name, entity_name.capitalize())
        if len(parts) >= 3:
            try:
                return entity_type, int(parts[2])
            except ValueError:
                pass
        return entity_type, 0

    return None, None


def _safe_body(body: bytes) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "<non-json body>"
    if isinstance(payload, dict):
        for key in ("password", "token", "access_token", "secret", "secret_key"):
            if key in payload:
                payload[key] = "[REDACTED]"
    return json.dumps(payload, ensure_ascii=False)[:10000]
