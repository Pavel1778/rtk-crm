from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "RTK CRM"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/rtk_crm"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Security
    secret_key: str = "change-me-in-production-32chars-min"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    encryption_key: str = ""

    # Keycloak
    keycloak_url: str = "http://keycloak:8080"
    keycloak_realm: str = "rtk-crm"
    keycloak_client_id: str = "rtk-crm-web"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # S3 / MinIO
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "rtk-crm-files"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    # Mode
    mock_mode: bool = True

    # Files
    max_file_size_mb: int = 50

    # Notifications
    stale_status_days: int = 14

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
