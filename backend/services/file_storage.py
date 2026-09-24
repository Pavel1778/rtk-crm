"""Хранилище файлов: MinIO/S3 с локальным fallback.

По Q&A Крылова файлы должны лежать в S3-совместимом хранилище (MinIO), а не
на локальном диске. В dev-режиме, если S3 не настроен, используется каталог
`uploads/`, чтобы приложение запускалось без инфраструктуры.
"""

from __future__ import annotations

import contextlib
import os
import uuid
from io import BytesIO
from pathlib import Path
from typing import Protocol

from app.core.config import get_settings


class Storage(Protocol):
    """Единый интерфейс хранилища для API файлов."""

    async def save(self, interaction_id: int, filename: str, content: bytes) -> str:
        """Сохраняет файл и возвращает ключ/путь для хранения в БД."""

    async def read(self, key: str) -> bytes:
        """Читает содержимое по ключу."""

    async def delete(self, key: str) -> None:
        """Удаляет объект, ошибки удаления не критичны."""

    async def ping(self) -> None:
        """Проверка доступности хранилища для /readyz."""


def _object_key(interaction_id: int, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"interactions/{interaction_id}/{uuid.uuid4()}{suffix}"


class LocalStorage:
    """Fallback: файлы на локальном диске (dev и локальный запуск)."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, interaction_id: int, filename: str, content: bytes) -> str:
        key = _object_key(interaction_id, filename)
        path = self.base_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    async def read(self, key: str) -> bytes:
        return (self.base_dir / key).read_bytes()

    async def delete(self, key: str) -> None:
        with contextlib.suppress(OSError):
            (self.base_dir / key).unlink()

    async def ping(self) -> None:
        return None


class S3Storage:
    """MinIO/S3-хранилище через minio-py (S3-совместимый API)."""

    def __init__(self) -> None:
        from minio import Minio

        settings = get_settings()
        self.bucket = settings.s3_bucket
        self.client = Minio(
            settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=settings.s3_secure,
        )
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    async def save(self, interaction_id: int, filename: str, content: bytes) -> str:
        key = _object_key(interaction_id, filename)
        self.client.put_object(
            self.bucket,
            key,
            BytesIO(content),
            length=len(content),
            content_type="application/octet-stream",
        )
        return key

    async def read(self, key: str) -> bytes:
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def delete(self, key: str) -> None:
        # Объект мог быть уже удалён — ошибка удаления не критична.
        with contextlib.suppress(Exception):
            self.client.remove_object(self.bucket, key)

    async def ping(self) -> None:
        self.client.bucket_exists(self.bucket)


_storage: Storage | None = None


def get_storage() -> Storage:
    """Возвращает singleton-хранилище: S3 при настройке, иначе локальное."""
    global _storage
    if _storage is not None:
        return _storage

    settings = get_settings()
    if settings.s3_enabled:
        _storage = S3Storage()
    else:
        base = Path(os.environ.get("UPLOAD_DIR", "uploads"))
        _storage = LocalStorage(base)
    return _storage


def reset_storage() -> None:
    """Сброс singleton (для тестов)."""
    global _storage
    _storage = None
