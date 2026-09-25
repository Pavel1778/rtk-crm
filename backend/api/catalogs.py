"""API для импорта каталогов из Excel и JSON файлов."""

import json
from datetime import datetime
from io import BytesIO

from app.auth.security import hash_password, require_manager_or_admin
from app.db.session import get_db
from app.models.entities import ITDirection, ITProduct, University, User
from app.models.enums import UserRole
from app.services.excel_import import (
    CATALOG_TYPES,
    CatalogImportResult,
    parse_catalog_file,
    parse_catalog_json,
)
from app.services.import_report import generate_import_report
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        catalog_type: 'universities', 'products' или 'users'
        file: Excel файл (.xlsx)

    Returns:
        dict с результатами парсинга и валидации
    """
    if catalog_type not in CATALOG_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "catalog_type должен быть 'universities', 'products' "
                "или 'users'"
            ),
        )

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате Excel (.xlsx или .xls)"
        )

    try:
        content = await file.read()
        file_bytes = BytesIO(content)

        result = parse_catalog_file(
            file_bytes,
            catalog_type,
            file.filename,
            _parse_mapping(mapping),
        )
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {e}") from e


@router.post("/import/report")
async def catalog_import_report(
    catalog_type: str,
    file: UploadFile = File(...),
    mapping: str = Form("{}"),
    _: User = Depends(require_manager_or_admin),
) -> StreamingResponse:
    """XLSX-отчёт о проблемах импорта: та же валидация, что в предпросмотре.

    Ошибки (пустое обязательное поле) блокируют строку, предупреждения
    (дубль в файле, некорректный email) — нет. Отчёт предназначен для
    менеджера каталога: можно исправить файл и загрузить его снова.
    """
    if catalog_type not in CATALOG_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "catalog_type должен быть 'universities', 'products' "
                "или 'users'"
            ),
        )
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате Excel (.xlsx или .xls)"
        )

    content = await file.read()
    result = parse_catalog_file(
        BytesIO(content),
        catalog_type,
        file.filename,
        _parse_mapping(mapping),
    )
    stream = generate_import_report(result)
    summary = result.to_dict()["summary"]
    filename = f"import-report-{datetime.now():%Y%m%d-%H%M}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Import-Error-Rows": str(summary["error_rows"]),
            "X-Import-Warning-Rows": str(summary["warning_rows"]),
        },
    )


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
        catalog_type: 'universities', 'products' или 'users'
        file: Excel файл (.xlsx)

    Returns:
        dict с результатами импорта
    """
    if catalog_type not in CATALOG_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                "catalog_type должен быть 'universities', 'products' "
                "или 'users'"
            ),
        )

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате Excel (.xlsx или .xls)"
        )

    try:
        content = await file.read()
        file_bytes = BytesIO(content)

        result = parse_catalog_file(
            file_bytes,
            catalog_type,
            file.filename,
            _parse_mapping(mapping),
        )

        if not result.success:
            return result.to_dict()

        return await _save_catalog_rows(result, catalog_type, db)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка импорта: {e}") from e


@router.post("/import/json/preview")
async def preview_json_catalog_import(
    catalog_type: str,
    file: UploadFile = File(...),
    mapping: str = Form("{}"),
    _: User = Depends(require_manager_or_admin),
) -> dict:
    """Предпросмотр JSON-импорта каталога без записи в БД."""
    if catalog_type not in CATALOG_TYPES:
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


# Временный пароль для пользователей из выгрузки. Выгрузка кейсодержателя не
# содержит паролей, поэтому учётная запись создаётся с временным паролем,
# который администратор обязан сменить при первой выдаче доступа.
_TEMP_USER_PASSWORD = "RtkTemp#2026"


def _normalise_user_role(raw: object) -> UserRole:
    """Приводит роль из выгрузки к значению перечисления.

    Заголовок «Роль» в файле кейсодержателя необязателен, а его значения
    могут быть человекочитаемыми («менеджер»). Неизвестное значение не
    должно ломать импорт — по умолчанию создаётся КАМ (минимальные права).
    """
    if raw in (None, ""):
        return UserRole.USER
    value = str(raw).strip().casefold()
    for role in UserRole:
        if value in (role.value, role.name.casefold()):
            return role
    aliases = {
        "администратор": UserRole.ADMIN,
        "админ": UserRole.ADMIN,
        "менеджер": UserRole.MANAGER,
        "кам": UserRole.USER,
        "пользователь": UserRole.USER,
    }
    return aliases.get(value, UserRole.USER)


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
    elif catalog_type == "users":
        for item in result.data:
            email = str(item["email"]).strip()
            existing = await db.scalar(
                select(User).where(User.email == email)
            )
            if existing:
                errors.append(f"Пользователь '{email}' уже существует")
                continue
            # Пароль из выгрузки не берём: файл кейсодержателя его не содержит,
            # а придумывать учётные данные за пользователя нельзя. Новый
            # пользователь создаётся с временным паролем и ролью КАМ.
            db.add(
                User(
                    email=email,
                    full_name=str(item["full_name"]).strip(),
                    hashed_password=hash_password(_TEMP_USER_PASSWORD),
                    role=_normalise_user_role(item.get("role")),
                )
            )
            created_count += 1
    else:
        raise HTTPException(status_code=400, detail="Неизвестный тип каталога")
    await db.commit()
    return {"success": True, "created": created_count, "total": len(result.data), "errors": errors}
