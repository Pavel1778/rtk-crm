import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""

    # Приложение
    app_name: str = "RTK CRM"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # База данных
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rtk_crm"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Безопасность
    secret_key: str = "change-me-in-production-32chars-min"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    encryption_key: str = ""

    # Keycloak
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "rtk-crm"
    keycloak_client_id: str = "rtk-crm-web"
    keycloak_client_secret: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # S3 / MinIO
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "rtk-crm-files"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    # Файлы
    max_file_size_mb: int = 50

    # Уведомления
    stale_status_days: int = 14

    # Режим работы
    mock_mode: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
