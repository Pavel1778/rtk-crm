"""Middleware для аудита действий (152-ФЗ)."""

import json
from typing import Callable

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import async_session_maker
from backend.models.entities import ActionLog, User


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
        try:
            # Получаем пользователя из контекста (если есть)
            user = getattr(request.state, "user", None)
            user_id = user.id if user else None
            
            # Определяем тип сущности и ID из пути
            entity_type, entity_id = _parse_entity_from_path(request.url.path)
            
            if entity_type and entity_id:
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
                async with async_session_maker() as session:
                    try:
                        # Ограничиваем размер тела для логирования
                        body_str = body.decode("utf-8", errors="ignore")[:10000] if body else None
                        
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
                    except Exception:
                        pass  # Не прерываем запрос при ошибке логирования
        except Exception:
            pass  # Не прерываем запрос при ошибках логирования
    
    return response


def _parse_entity_from_path(path: str) -> tuple[str | None, int | None]:
    """Парсит путь и возвращает тип сущности и ID."""
    # Примеры путей:
    # /api/interactions/123 -> ("Interaction", 123)
    # /api/universities/456 -> ("University", 456)
    # /api/files/789 -> ("AttachedFile", 789)
    
    parts = path.strip("/").split("/")
    if len(parts) >= 3:
        entity_name = parts[1]  # interactions, universities, etc.
        entity_id_str = parts[2]
        
        try:
            entity_id = int(entity_id_str)
            
            # Конвертация имени в тип модели
            entity_map = {
                "interactions": "Interaction",
                "universities": "University",
                "files": "AttachedFile",
                "actions": "Action",
                "comments": "Comment",
                "stages": "WorkflowStageRef",
                "products": "ITProduct",
                "directions": "ITDirection",
            }
            
            entity_type = entity_map.get(entity_name, entity_name.capitalize())
            return entity_type, entity_id
        except (ValueError, IndexError):
            pass
    
    return None, None
