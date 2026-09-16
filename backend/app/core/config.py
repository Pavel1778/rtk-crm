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
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,https://rtk-crm.vercel.app,https://rtk-crm-nx4r.vercel.app"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Debug
    DEBUG: bool = False

    # File storage
    FILE_STORAGE_PATH: str = "/app/files"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
