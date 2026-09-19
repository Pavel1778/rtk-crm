"""API для импорта каталогов из Excel файлов."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import get_current_user
from backend.db.session import get_db
from backend.models.entities import ITDirection, ITProduct, University, User
from backend.schemas.entities import ITProductCreate, UniversityCreate
from backend.services.excel_import import parse_catalog_file, CatalogImportResult

router = APIRouter(prefix="/api/catalogs", tags=["catalogs"])


@router.post("/import/preview")
async def preview_catalog_import(
    catalog_type: str,
    file: UploadFile = File(...),
    current: User = Depends(get_current_user),
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
    
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате Excel (.xlsx или .xls)"
        )
    
    try:
        content = await file.read()
        from io import BytesIO
        file_bytes = BytesIO(content)
        
        result = parse_catalog_file(file_bytes, catalog_type)
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")


@router.post("/import/execute")
async def execute_catalog_import(
    catalog_type: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
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
    
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате Excel (.xlsx или .xls)"
        )
    
    try:
        content = await file.read()
        from io import BytesIO
        file_bytes = BytesIO(content)
        
        result = parse_catalog_file(file_bytes, catalog_type)
        
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
