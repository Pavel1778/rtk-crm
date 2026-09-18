"""
S3-клиент для работы с MinIO (совместимый с AWS S3).
Используется для хранения прикреплённых файлов взаимодействий.
"""
import io
from typing import Optional
from loguru import logger
from minio import Minio
from minio.error import S3Error
from app.core.config import settings


class S3Client:
    """Клиент для работы с S3-совместимым хранилищем (MinIO)."""

    def __init__(self):
        self.client: Optional[Minio] = None
        self.bucket_name = settings.S3_BUCKET
        self._initialize()

    def _initialize(self) -> None:
        """Инициализация клиента MinIO."""
        if not settings.S3_ENDPOINT:
            logger.warning("S3_ENDPOINT не настроен, клиент S3 не будет инициализирован")
            return

        try:
            self.client = Minio(
                endpoint=settings.S3_ENDPOINT.replace("http://", "").replace("https://", ""),
                access_key=settings.S3_ACCESS_KEY,
                secret_key=settings.S3_SECRET_KEY,
                secure=settings.S3_USE_SSL,
            )
            # Создаём бакет, если не существует
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Бакет {self.bucket_name} создан")
        except Exception as e:
            logger.error(f"Ошибка инициализации S3 клиента: {e}")
            self.client = None

    async def upload_file(
        self,
        file_data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> bool:
        """
        Загрузка файла в хранилище.

        :param file_data: Байты файла
        :param object_name: Имя объекта в бакете
        :param content_type: MIME-тип файла
        :return: True если успешно
        """
        if not self.client:
            logger.error("S3 клиент не инициализирован")
            return False

        try:
            data = io.BytesIO(file_data)
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=data,
                length=len(file_data),
                content_type=content_type,
            )
            logger.info(f"Файл {object_name} загружен в бакет {self.bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"Ошибка загрузки файла в S3: {e}")
            return False

    async def download_file(self, object_name: str) -> Optional[bytes]:
        """
        Скачивание файла из хранилища.

        :param object_name: Имя объекта в бакете
        :return: Байты файла или None
        """
        if not self.client:
            logger.error("S3 клиент не инициализирован")
            return None

        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Ошибка скачивания файла из S3: {e}")
            return None

    async def delete_file(self, object_name: str) -> bool:
        """
        Удаление файла из хранилища.

        :param object_name: Имя объекта в бакете
        :return: True если успешно
        """
        if not self.client:
            logger.error("S3 клиент не инициализирован")
            return False

        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
            logger.info(f"Файл {object_name} удалён из бакета {self.bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"Ошибка удаления файла из S3: {e}")
            return False

    async def get_presigned_url(
        self, object_name: str, expires_in: int = 3600
    ) -> Optional[str]:
        """
        Получение временной ссылки на файл.

        :param object_name: Имя объекта в бакете
        :param expires_in: Время действия ссылки в секундах
        :return: URL или None
        """
        if not self.client:
            logger.error("S3 клиент не инициализирован")
            return None

        try:
            from datetime import timedelta

            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(seconds=expires_in),
            )
            return url
        except S3Error as e:
            logger.error(f"Ошибка получения presigned URL: {e}")
            return None


# Глобальный экземпляр
s3_client = S3Client()
