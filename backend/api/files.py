"""API для прикрепления файлов к взаимодействиям."""

import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.security import get_current_user
from backend.db.session import get_db
from backend.models.entities import AttachedFile, Interaction, User
from backend.schemas.entities import AttachedFileRead

router = APIRouter(prefix="/api/files", tags=["files"])

# Разрешённые MIME-типы
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "application/pdf",
    "application/zip",
    "application/gzip",
    "application/x-rar-compressed",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# Максимальный размер файла (50 МБ)
MAX_FILE_SIZE = 50 * 1024 * 1024

# Директория для хранения файлов
UPLOAD_DIR = Path("/app/uploads")
if not UPLOAD_DIR.exists():
    # Fallback для локальной разработки
    UPLOAD_DIR = Path("uploads")
    UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/interactions/{interaction_id}/upload", response_model=AttachedFileRead, status_code=201)
async def upload_file(
    interaction_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> AttachedFileRead:
    """Загрузка файла к взаимодействию."""
    
    # Проверка взаимодействия
    interaction = await db.get(Interaction, interaction_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="Взаимодействие не найдено")
    
    # Проверка MIME-типа
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый тип файла: {file.content_type}. Разрешены: {', '.join(ALLOWED_MIME_TYPES)}"
        )
    
    # Чтение содержимого файла
    content = await file.read()
    
    # Проверка размера
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимум: {MAX_FILE_SIZE / (1024*1024)} МБ"
        )
    
    # Генерация уникального имени файла
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    
    # Создание директории для взаимодействия
    interaction_dir = UPLOAD_DIR / str(interaction_id)
    interaction_dir.mkdir(exist_ok=True)
    
    # Сохранение файла
    file_path = interaction_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Создание записи в БД
    attached_file = AttachedFile(
        interaction_id=interaction_id,
        filename=file.filename,
        file_path=str(file_path),
        size=len(content),
        mime_type=file.content_type,
        uploaded_by=current.id,
    )
    db.add(attached_file)
    await db.commit()
    await db.refresh(attached_file)
    
    # Получение имени загрузчика
    uploader = await db.get(User, current.id)
    
    return AttachedFileRead(
        id=attached_file.id,
        interaction_id=attached_file.interaction_id,
        filename=attached_file.filename,
        size=attached_file.size,
        mime_type=attached_file.mime_type,
        uploaded_by=attached_file.uploaded_by,
        uploader_name=uploader.full_name if uploader else None,
        created_at=attached_file.created_at,
    )


@router.get("/interactions/{interaction_id}", response_model=list[AttachedFileRead])
async def list_files(
    interaction_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AttachedFileRead]:
    """Список файлов взаимодействия."""
    
    # Проверка взаимодействия
    interaction = await db.get(Interaction, interaction_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="Взаимодействие не найдено")
    
    # Получение файлов
    files = list(
        await db.scalars(
            select(AttachedFile)
            .where(AttachedFile.interaction_id == interaction_id)
            .order_by(AttachedFile.created_at.desc())
        )
    )
    
    # Добавление имён загрузчиков
    result = []
    for file in files:
        uploader = await db.get(User, file.uploaded_by) if file.uploaded_by else None
        result.append(
            AttachedFileRead(
                id=file.id,
                interaction_id=file.interaction_id,
                filename=file.filename,
                size=file.size,
                mime_type=file.mime_type,
                uploaded_by=file.uploaded_by,
                uploader_name=uploader.full_name if uploader else None,
                created_at=file.created_at,
            )
        )
    
    return result


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Скачивание файла."""
    
    attached_file = await db.get(AttachedFile, file_id)
    if attached_file is None:
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    file_path = Path(attached_file.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден на диске")
    
    return FileResponse(
        path=file_path,
        filename=attached_file.filename,
        media_type=attached_file.mime_type,
    )


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> None:
    """Удаление файла."""
    
    attached_file = await db.get(AttachedFile, file_id)
    if attached_file is None:
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    # Проверка прав (admin или автор)
    if not current.is_admin and attached_file.uploaded_by != current.id:
        raise HTTPException(
            status_code=403,
            detail="Можно удалять только свои файлы"
        )
    
    # Удаление с диска
    file_path = Path(attached_file.file_path)
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception:
            pass  # Игнорируем ошибки удаления с диска
    
    # Удаление из БД
    await db.delete(attached_file)
    await db.commit()
