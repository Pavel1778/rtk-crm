"""API для импорта каталогов из Excel и JSON файлов."""

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import require_manager_or_admin
from app.db.session import get_db
from app.models.entities import ITDirection, ITProduct, University, User
from app.schemas.entities import ITProductCreate, UniversityCreate
from app.services.excel_import import (
    CatalogImportResult,
    parse_catalog_file,
    parse_catalog_json,
)

router = APIRouter(prefix="/api/catalogs", tags=["catalogs"])


@router.post("/import/preview")
async def preview_catalog_import(
    catalog_type: str,
    file: UploadFile = File(...),
    mapping: str = Form("{}"),
    current: User = Depends(require_manager_or_admin),
) -> dict:
    """Предпросмотр импорта каталога (валидация без сохранения).
    
    Args:
        catalog_type: 'universities' или 'products'
        file: Excel файл (.xlsx)
    
    Returns:
        dict с результатами парсинга и валидации
    """
    if catalog_type not in ["universities", "products"]:
        raise HTTPException(
            status_code=400,
            detail="catalog_type должен быть 'universities' или 'products'"
        )
    
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате Excel (.xlsx или .xls)"
        )
    
    try:
        content = await file.read()
        from io import BytesIO
        file_bytes = BytesIO(content)
        
        result = parse_catalog_file(
            file_bytes,
            catalog_type,
            file.filename,
            _parse_mapping(mapping),
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")


@router.post("/import/execute")
async def execute_catalog_import(
    catalog_type: str,
    file: UploadFile = File(...),
    mapping: str = Form("{}"),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_manager_or_admin),
) -> dict:
    """Выполнение импорта каталога (с сохранением в БД).
    
    Args:
        catalog_type: 'universities' или 'products'
        file: Excel файл (.xlsx)
    
    Returns:
        dict с результатами импорта
    """
    if catalog_type not in ["universities", "products"]:
        raise HTTPException(
            status_code=400,
            detail="catalog_type должен быть 'universities' или 'products'"
        )
    
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате Excel (.xlsx или .xls)"
        )
    
    try:
        content = await file.read()
        from io import BytesIO
        file_bytes = BytesIO(content)
        
        result = parse_catalog_file(
            file_bytes,
            catalog_type,
            file.filename,
            _parse_mapping(mapping),
        )
        
        if not result.success:
            return result.to_dict()
        
        created_count = 0
        errors = result.errors.copy()
        
        if catalog_type == "universities":
            for item in result.data:
                try:
                    # Проверяем дубликаты по названию
                    existing = await db.scalar(
                        select(University).where(University.name == item["name"])
                    )
                    if existing:
                        errors.append(f"Вуз '{item['name']}' уже существует")
                        continue
                    
                    university = University(
                        name=item["name"],
                        city=item.get("city"),
                        contact_person=item.get("contact_person"),
                        contact_email=item.get("contact_email"),
                        contact_phone=item.get("contact_phone"),
                    )
                    db.add(university)
                    created_count += 1
                except Exception as e:
                    errors.append(f"Ошибка создания вуза '{item.get('name')}': {str(e)}")
        
        elif catalog_type == "products":
            for item in result.data:
                try:
                    # Проверяем дубликаты по названию
                    existing = await db.scalar(
                        select(ITProduct).where(ITProduct.name == item["name"])
                    )
                    if existing:
                        errors.append(f"Продукт '{item['name']}' уже существует")
                        continue
                    
                    # Находим или создаём направление
                    direction = None
                    if item.get("direction"):
                        direction = await db.scalar(
                            select(ITDirection).where(ITDirection.name == item["direction"])
                        )
                        if not direction:
                            direction = ITDirection(name=item["direction"])
                            db.add(direction)
                            await db.flush()
                    
                    product = ITProduct(
                        name=item["name"],
                        direction_id=direction.id if direction else None,
                    )
                    db.add(product)
                    created_count += 1
                except Exception as e:
                    errors.append(f"Ошибка создания продукта '{item.get('name')}': {str(e)}")
        
        await db.commit()
        
        return {
            "success": True,
            "created": created_count,
            "total": len(result.data),
            "errors": errors,
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка импорта: {str(e)}")


@router.post("/import/json/preview")
async def preview_json_catalog_import(
    catalog_type: str,
    file: UploadFile = File(...),
    mapping: str = Form("{}"),
    _: User = Depends(require_manager_or_admin),
) -> dict:
    """Предпросмотр JSON-импорта каталога без записи в БД."""
    if catalog_type not in {"universities", "products"}:
        raise HTTPException(status_code=400, detail="Неизвестный тип каталога")
    result = parse_catalog_json(
        await file.read(),
        catalog_type,
        _parse_mapping(mapping),
    )
    return result.to_dict()


@router.post("/import/json/execute")
async def execute_json_catalog_import(
    catalog_type: str,
    file: UploadFile = File(...),
    mapping: str = Form("{}"),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_manager_or_admin),
) -> dict:
    """Выполнение JSON-импорта через общий путь сохранения каталога."""
    result = parse_catalog_json(
        await file.read(),
        catalog_type,
        _parse_mapping(mapping),
    )
    if not result.success:
        return result.to_dict()
    return await _save_catalog_rows(result, catalog_type, db)


def _parse_mapping(raw_mapping: str) -> dict[str, str] | None:
    try:
        value = json.loads(raw_mapping or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Некорректный mapping: {exc}") from exc
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(source, str)
        for key, source in value.items()
    ):
        raise HTTPException(status_code=400, detail="mapping должен быть объектом строк")
    return value or None


async def _save_catalog_rows(
    result: CatalogImportResult,
    catalog_type: str,
    db: AsyncSession,
) -> dict:
    created_count = 0
    errors = result.errors.copy()
    if catalog_type == "universities":
        for item in result.data:
            existing = await db.scalar(
                select(University).where(University.name == item["name"])
            )
            if existing:
                errors.append(f"Вуз '{item['name']}' уже существует")
                continue
            db.add(University(
                name=item["name"],
                city=item.get("city"),
                contact_person=item.get("contact_person"),
                contact_email=item.get("contact_email"),
                contact_phone=item.get("contact_phone"),
            ))
            created_count += 1
    elif catalog_type == "products":
        for item in result.data:
            existing = await db.scalar(
                select(ITProduct).where(ITProduct.name == item["name"])
            )
            if existing:
                errors.append(f"Продукт '{item['name']}' уже существует")
                continue
            direction = None
            if item.get("direction"):
                direction = await db.scalar(
                    select(ITDirection).where(ITDirection.name == item["direction"])
                )
                if not direction:
                    direction = ITDirection(name=item["direction"])
                    db.add(direction)
                    await db.flush()
            db.add(ITProduct(
                name=item["name"],
                direction_id=direction.id if direction else None,
            ))
            created_count += 1
    else:
        raise HTTPException(status_code=400, detail="Неизвестный тип каталога")
    await db.commit()
    return {"success": True, "created": created_count, "total": len(result.data), "errors": errors}
