from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://rtk_user:rtk_password@localhost:5432/rtk_crm"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # Debug
    DEBUG: bool = False

    # File storage
    FILE_STORAGE_PATH: str = "/app/files"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
