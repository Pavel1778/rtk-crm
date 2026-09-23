"""API для прикрепления файлов к взаимодействиям."""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import get_current_user
from app.api.access import get_accessible_interaction
from app.db.session import get_db
from app.models.entities import AttachedFile, User
from app.schemas.entities import AttachedFileRead
from app.services.file_storage import get_storage

router = APIRouter(prefix="/api/files", tags=["files"])

# Разрешённые MIME-типы
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "application/pdf",
    "application/zip",
    "application/gzip",
    "application/x-rar-compressed",
    "application/vnd.rar",
    "application/x-gzip",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
ALLOWED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".zip",
    ".gz",
    ".rar",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
}

# Максимальный размер файла (50 МБ)
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/interactions/{interaction_id}/upload", response_model=AttachedFileRead, status_code=201)
async def upload_file(
    interaction_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> AttachedFileRead:
    """Загрузка файла к взаимодействию."""

    # Проверка взаимодействия и прав на него
    await get_accessible_interaction(db, interaction_id, current)

    # Проверка MIME-типа
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()
    if (
        file.content_type not in ALLOWED_MIME_TYPES
        or extension not in ALLOWED_EXTENSIONS
    ):
        raise HTTPException(
            status_code=400,
            detail="Недопустимый формат файла. Разрешены PNG, JPEG, PDF, ZIP, GZIP, RAR, DOC, DOCX, XLS и XLSX",
        )

    # Чтение содержимого файла
    content = await file.read()

    # Проверка размера
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимум: {MAX_FILE_SIZE / (1024*1024)} МБ"
        )

    # Сохранение в S3/MinIO либо в локальный uploads/ (fallback).
    storage = get_storage()


    storage_key = await storage.save(interaction_id, filename, content)

    # Создание записи в БД
    attached_file = AttachedFile(
        interaction_id=interaction_id,
        filename=filename,
        file_path=storage_key,
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
    current: User = Depends(get_current_user),
) -> list[AttachedFileRead]:
    """Список файлов взаимодействия."""

    await get_accessible_interaction(db, interaction_id, current)

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
    current: User = Depends(get_current_user),
):
    """Скачивание файла."""

    attached_file = await db.get(AttachedFile, file_id)
    if attached_file is None:
        raise HTTPException(status_code=404, detail="Файл не найден")

    # Файл наследует доступ своего взаимодействия.
    await get_accessible_interaction(db, attached_file.interaction_id, current)

    try:
        content = await get_storage().read(attached_file.file_path)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=404, detail="Файл не найден в хранилище")

    # Отдаём байты напрямую: работает и для локального диска, и для S3,
    # где локального пути не существует.
    return Response(
        content=content,
        media_type=attached_file.mime_type,
        headers={
            "Content-Disposition": _attachment_header(attached_file.filename)
        },
    )


def _attachment_header(filename: str) -> str:
    """RFC 5987: ASCII-фолбэк + UTF-8 имя для кириллических имён файлов."""
    from urllib.parse import quote

    fallback = filename.encode("ascii", "ignore").decode() or "file"
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"


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

    # Удаление из S3/MinIO или локального каталога
    await get_storage().delete(attached_file.file_path)

    # Удаление из БД
    await db.delete(attached_file)
    await db.commit()
